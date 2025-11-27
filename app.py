"""
Oracle Cloud Instance Manager - Admin Panel
Multi-account support with separate .env files for each OCI account
"""

import os
import sys
import json
import time
import logging
import threading
import secrets
import glob
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv, set_key, dotenv_values
import oci

import random

# Load main environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Accounts directory
ACCOUNTS_DIR = os.getenv('ACCOUNTS_DIR', './accounts')
os.makedirs(ACCOUNTS_DIR, exist_ok=True)

# Global state - now per account
bot_threads = {}  # account_id -> thread
bot_status = {}   # account_id -> status dict
logs_buffer = {}  # account_id -> list of logs
MAX_LOGS = 500

# ======================== LOGGING SETUP ======================== #

class SocketIOHandler(logging.Handler):
    """Custom handler to emit logs via WebSocket"""
    def __init__(self, account_id=None):
        super().__init__()
        self.account_id = account_id
    
    def emit(self, record):
        try:
            log_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'level': record.levelname,
                'message': self.format(record),
                'account_id': self.account_id
            }
            
            if self.account_id:
                if self.account_id not in logs_buffer:
                    logs_buffer[self.account_id] = []
                logs_buffer[self.account_id].append(log_entry)
                if len(logs_buffer[self.account_id]) > MAX_LOGS:
                    logs_buffer[self.account_id].pop(0)
            
            socketio.emit('log_message', log_entry, namespace='/logs')
        except Exception:
            pass

# Main logger
logger = logging.getLogger('oci_manager')
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s'))
logger.addHandler(console_handler)

def get_account_logger(account_id):
    """Get or create a logger for specific account"""
    account_logger = logging.getLogger(f'oci_manager.{account_id}')
    account_logger.setLevel(logging.INFO)
    
    # Check if handler already exists
    if not account_logger.handlers:
        socket_handler = SocketIOHandler(account_id)
        socket_handler.setFormatter(logging.Formatter('%(message)s'))
        account_logger.addHandler(socket_handler)
        account_logger.addHandler(console_handler)
    
    return account_logger

# ======================== AUTHENTICATION ======================== #

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_credentials():
    """Get admin credentials from env"""
    username = os.getenv('WEB_USERNAME', 'admin')
    password = os.getenv('WEB_PASSWORD', 'admin123')
    return username, password

# ======================== ACCOUNT MANAGEMENT ======================== #

def get_accounts():
    """Get list of all accounts"""
    accounts = []
    env_files = glob.glob(os.path.join(ACCOUNTS_DIR, '*.env'))
    
    for env_file in env_files:
        account_id = os.path.basename(env_file).replace('.env', '')
        config = dotenv_values(env_file)
        
        # Get bot status for this account
        status = bot_status.get(account_id, {
            'running': False,
            'start_time': None,
            'retry_count': 0,
            'last_error': None,
            'last_check': None,
            'current_ad': None
        })
        
        accounts.append({
            'id': account_id,
            'name': config.get('ACCOUNT_NAME', account_id),
            'region': config.get('OCI_REGION', 'Unknown'),
            'shape': config.get('OCI_SHAPE', 'Unknown'),
            'ocpus': config.get('OCI_OCPUS', '0'),
            'memory': config.get('OCI_MEMORY_IN_GBS', '0'),
            'status': status,
            'file': env_file
        })
    
    return accounts

def get_account_config(account_id):
    """Get configuration for specific account"""
    env_file = os.path.join(ACCOUNTS_DIR, f'{account_id}.env')
    if os.path.exists(env_file):
        return dotenv_values(env_file)
    return None

def save_account_config(account_id, config):
    """Save configuration for specific account"""
    env_file = os.path.join(ACCOUNTS_DIR, f'{account_id}.env')
    
    # Write all config values
    with open(env_file, 'w') as f:
        for key, value in config.items():
            if value:
                # Handle multiline values (like SSH keys)
                if '\n' in str(value):
                    f.write(f'{key}="{value}"\n')
                else:
                    f.write(f'{key}={value}\n')
    
    return True

def delete_account(account_id):
    """Delete an account"""
    # Stop bot if running
    if account_id in bot_status and bot_status[account_id].get('running'):
        stop_bot(account_id)
    
    env_file = os.path.join(ACCOUNTS_DIR, f'{account_id}.env')
    if os.path.exists(env_file):
        os.remove(env_file)
        return True
    return False

def generate_account_id():
    """Generate unique account ID"""
    return f"account_{int(time.time())}_{secrets.token_hex(4)}"

# ======================== OCI HELPERS ======================== #

def get_oci_config(account_id):
    """Build OCI config from account environment variables"""
    config = get_account_config(account_id)
    if not config:
        return None
    
    return {
        'user': config.get('OCI_USER_ID', ''),
        'key_file': config.get('OCI_PRIVATE_KEY_FILENAME', ''),
        'fingerprint': config.get('OCI_KEY_FINGERPRINT', ''),
        'tenancy': config.get('OCI_TENANCY_ID', ''),
        'region': config.get('OCI_REGION', 'eu-frankfurt-1')
    }

def test_oci_connection(account_id):
    """Test OCI API connection for specific account"""
    try:
        config = get_oci_config(account_id)
        if not config:
            return False, "Account not found"
        
        identity = oci.identity.IdentityClient(config)
        tenancy = identity.get_tenancy(tenancy_id=config['tenancy']).data
        return True, {'name': tenancy.name, 'description': tenancy.description}
    except Exception as e:
        return False, str(e)

def get_oci_instances(account_id):
    """Get list of OCI instances for specific account"""
    try:
        config = get_oci_config(account_id)
        if not config:
            return []
        
        account_config = get_account_config(account_id)
        compute = oci.core.ComputeClient(config)
        compartment_id = account_config.get('OCI_TENANCY_ID', config.get('tenancy', ''))
        instances = compute.list_instances(compartment_id=compartment_id).data
        
        result = []
        for inst in instances:
            result.append({
                'id': inst.id,
                'name': inst.display_name,
                'shape': inst.shape,
                'state': inst.lifecycle_state,
                'ocpus': int(inst.shape_config.ocpus) if inst.shape_config else 'N/A',
                'memory': int(inst.shape_config.memory_in_gbs) if inst.shape_config else 'N/A',
                'created': inst.time_created.strftime('%Y-%m-%d %H:%M') if inst.time_created else 'N/A',
                'ad': inst.availability_domain
            })
        return result
    except Exception as e:
        logger.error(f"Failed to get instances for {account_id}: {e}")
        return []

def get_availability_domains(account_id):
    """Get available ADs for specific account"""
    try:
        config = get_oci_config(account_id)
        if not config:
            return []
        
        account_config = get_account_config(account_id)
        identity = oci.identity.IdentityClient(config)
        compartment_id = account_config.get('OCI_TENANCY_ID', config.get('tenancy', ''))
        ads = identity.list_availability_domains(compartment_id=compartment_id).data
        return [{'name': ad.name, 'id': ad.id} for ad in ads]
    except Exception as e:
        logger.error(f"Failed to get ADs for {account_id}: {e}")
        return []

def get_storage_info(account_id):
    """Get storage usage info for specific account"""
    try:
        config = get_oci_config(account_id)
        if not config:
            return {'used': 0, 'total': 200, 'free': 200, 'percentage': 0}
        
        account_config = get_account_config(account_id)
        volume_client = oci.core.BlockstorageClient(config)
        compartment_id = account_config.get('OCI_TENANCY_ID', config.get('tenancy', ''))
        
        total_size = 0
        
        # Block volumes
        volumes = volume_client.list_volumes(compartment_id=compartment_id).data
        for vol in volumes:
            if vol.lifecycle_state not in ('TERMINATING', 'TERMINATED'):
                total_size += vol.size_in_gbs
        
        # Boot volumes (all ADs)
        ads = get_availability_domains(account_id)
        for ad in ads:
            try:
                boot_vols = volume_client.list_boot_volumes(
                    availability_domain=ad['name'],
                    compartment_id=compartment_id
                ).data
                for bvol in boot_vols:
                    if bvol.lifecycle_state not in ('TERMINATING', 'TERMINATED'):
                        total_size += bvol.size_in_gbs
            except:
                pass
        
        return {
            'used': total_size,
            'total': 200,
            'free': 200 - total_size,
            'percentage': round((total_size / 200) * 100, 1)
        }
    except Exception as e:
        logger.error(f"Failed to get storage info for {account_id}: {e}")
        return {'used': 0, 'total': 200, 'free': 200, 'percentage': 0}

def get_compute_limits(account_id):
    """Get compute resource limits for specific account"""
    try:
        instances = get_oci_instances(account_id)
        account_config = get_account_config(account_id)
        shape = account_config.get('OCI_SHAPE', 'VM.Standard.A1.Flex') if account_config else 'VM.Standard.A1.Flex'
        
        if 'A1.Flex' in shape:
            max_ocpus, max_memory = 4, 24
        elif 'E2.1.Micro' in shape:
            max_ocpus, max_memory = 2, 2
        else:
            max_ocpus, max_memory = 4, 24
        
        used_ocpus = sum(i['ocpus'] for i in instances if i['state'] not in ('TERMINATING', 'TERMINATED') and isinstance(i['ocpus'], int))
        used_memory = sum(i['memory'] for i in instances if i['state'] not in ('TERMINATING', 'TERMINATED') and isinstance(i['memory'], int))
        
        return {
            'ocpus': {'used': used_ocpus, 'max': max_ocpus, 'free': max_ocpus - used_ocpus},
            'memory': {'used': used_memory, 'max': max_memory, 'free': max_memory - used_memory}
        }
    except Exception as e:
        logger.error(f"Failed to get compute limits for {account_id}: {e}")
        return {
            'ocpus': {'used': 0, 'max': 4, 'free': 4},
            'memory': {'used': 0, 'max': 24, 'free': 24}
        }

# ======================== BOT MANAGEMENT ======================== #

def run_bot_thread(account_id):
    """Run the bot for a specific account"""
    global bot_status
    
    account_logger = get_account_logger(account_id)
    account_config = get_account_config(account_id)
    
    if not account_config:
        account_logger.error(f"Account {account_id} not found")
        return
    
    config = get_oci_config(account_id)
    if not config:
        account_logger.error(f"Failed to get OCI config for {account_id}")
        return
    
    # Get settings from account config
    shape = account_config.get('OCI_SHAPE', 'VM.Standard.A1.Flex')
    ocpus = int(account_config.get('OCI_OCPUS', 4))
    memory = int(account_config.get('OCI_MEMORY_IN_GBS', 24))
    image_id = account_config.get('OCI_IMAGE_ID', '')
    subnet_id = account_config.get('OCI_SUBNET_ID', '')
    ssh_key = account_config.get('OCI_SSH_PUBLIC_KEY', '')
    compartment_id = account_config.get('OCI_TENANCY_ID', config.get('tenancy', ''))
    display_name = account_config.get('OCI_DISPLAY_NAME', f'instance-{int(time.time())}')
    account_name = account_config.get('ACCOUNT_NAME', account_id)
    
    bot_token = account_config.get('TELEGRAM_BOT_API_KEY', '')
    telegram_uid = account_config.get('TELEGRAM_USER_ID', '')
    
    bot = None
    if bot_token and telegram_uid:
        try:
            import telebot
            bot = telebot.TeleBot(bot_token)
        except:
            pass
    
    try:
        compute_client = oci.core.ComputeClient(config)
        vcn_client = oci.core.VirtualNetworkClient(config)
        identity_client = oci.identity.IdentityClient(config)
    except Exception as e:
        account_logger.error(f"Failed to initialize OCI clients: {e}")
        bot_status[account_id]['running'] = False
        return
    
    # Get availability domains
    try:
        ads = identity_client.list_availability_domains(compartment_id=compartment_id).data
        ad_names = [ad.name for ad in ads]
    except Exception as e:
        account_logger.error(f"Failed to get availability domains: {e}")
        bot_status[account_id]['running'] = False
        return
    
    # Custom AD from config
    custom_ad = account_config.get('OCI_AVAILABILITY_DOMAIN', '')
    if custom_ad:
        ad_names = [custom_ad]
    
    wait_time = int(account_config.get('OCI_RETRY_INTERVAL', 30))
    min_wait = int(account_config.get('OCI_MIN_RETRY_INTERVAL', 10))
    max_wait = int(account_config.get('OCI_MAX_RETRY_INTERVAL', 120))
    
    account_logger.info(f"[{account_name}] Starting bot for shape: {shape}, {ocpus} OCPUs, {memory} GB RAM")
    account_logger.info(f"[{account_name}] Availability Domains: {len(ad_names)} found")
    
    # Send Telegram notification
    if bot and telegram_uid:
        try:
            bot.send_message(telegram_uid, f"🚀 [{account_name}] Bot started!\nShape: {shape}\nOCPUs: {ocpus}\nMemory: {memory} GB")
        except:
            pass
    
    retry_count = 0
    tc = oc = 0
    
    while bot_status.get(account_id, {}).get('running', False):
        for ad in ad_names:
            if not bot_status.get(account_id, {}).get('running', False):
                break
            
            bot_status[account_id]['current_ad'] = ad
            bot_status[account_id]['last_check'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Build source details
            source_details = oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=image_id
            )
            
            instance_details = oci.core.models.LaunchInstanceDetails(
                metadata={"ssh_authorized_keys": ssh_key},
                availability_domain=ad,
                shape=shape,
                compartment_id=compartment_id,
                display_name=display_name,
                is_pv_encryption_in_transit_enabled=True,
                source_details=source_details,
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    assign_public_ip=True,
                    subnet_id=subnet_id
                ),
                shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                    ocpus=ocpus,
                    memory_in_gbs=memory
                )
            )
            
            try:
                response = compute_client.launch_instance(instance_details)
                instance_id = response.data.id
                
                account_logger.info(f"[{account_name}] ✅ Instance launched! ID: {instance_id}")
                
                # Wait for instance to be running
                time.sleep(60)
                
                # Get public IP
                try:
                    vnic_attachments = compute_client.list_vnic_attachments(
                        compartment_id=compartment_id,
                        instance_id=instance_id
                    ).data
                    
                    if vnic_attachments:
                        private_ips = vcn_client.list_private_ips(
                            subnet_id=subnet_id,
                            vnic_id=vnic_attachments[0].vnic_id
                        ).data
                        
                        if private_ips:
                            public_ip_obj = vcn_client.get_public_ip_by_private_ip_id(
                                oci.core.models.GetPublicIpByPrivateIpIdDetails(
                                    private_ip_id=private_ips[0].id
                                )
                            ).data
                            public_ip = public_ip_obj.ip_address
                        else:
                            public_ip = "Pending..."
                    else:
                        public_ip = "Pending..."
                except:
                    public_ip = "Pending..."
                
                success_msg = f"[{account_name}] 🎉 Instance created!\nName: {display_name}\nShape: {shape}\nIP: {public_ip}\nRetries: {retry_count}"
                account_logger.info(success_msg)
                
                if bot and telegram_uid:
                    try:
                        bot.send_message(telegram_uid, success_msg)
                    except:
                        pass
                
                bot_status[account_id]['running'] = False
                socketio.emit('bot_status', {'account_id': account_id, 'status': bot_status[account_id]}, namespace='/logs')
                return
                
            except oci.exceptions.ServiceError as e:
                retry_count += 1
                bot_status[account_id]['retry_count'] = retry_count
                bot_status[account_id]['last_error'] = f"{e.code}: {e.message}"
                
                # Adaptive wait time with randomization
                if e.status == 429:
                    # Rate limited - increase base wait time
                    oc = 0
                    tc += 1
                    if tc >= 2:
                        wait_time = min(wait_time + 10, max_wait)
                        tc = 0
                else:
                    tc = 0
                    if wait_time > min_wait:
                        oc += 1
                    if oc >= 2:
                        wait_time = max(min_wait, wait_time - 5)
                        oc = 0
                
                # Random wait between min_wait and current wait_time
                actual_wait = random.randint(min_wait, max(min_wait, wait_time))
                
                ad_short = ad.split(':')[-1] if ':' in ad else ad
                account_logger.info(f"[{account_name}] ❌ {e.status} - {e.code} | AD: {ad_short} | Retry #{retry_count} | Wait: {actual_wait}s")
                
                socketio.emit('bot_status', {'account_id': account_id, 'status': bot_status[account_id]}, namespace='/logs')
                time.sleep(actual_wait)
                
            except Exception as e:
                retry_count += 1
                bot_status[account_id]['retry_count'] = retry_count
                bot_status[account_id]['last_error'] = str(e)
                actual_wait = random.randint(min_wait, max(min_wait, wait_time))
                account_logger.error(f"[{account_name}] Error: {e} | Retry #{retry_count} | Wait: {actual_wait}s")
                socketio.emit('bot_status', {'account_id': account_id, 'status': bot_status[account_id]}, namespace='/logs')
                time.sleep(actual_wait)
    
    account_logger.info(f"[{account_name}] Bot stopped")

def start_bot(account_id):
    """Start the bot for a specific account"""
    global bot_status, bot_threads
    
    if account_id in bot_status and bot_status[account_id].get('running'):
        return False, "Bot is already running"
    
    bot_status[account_id] = {
        'running': True,
        'start_time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'retry_count': 0,
        'last_error': None,
        'last_check': None,
        'current_ad': None
    }
    
    thread = threading.Thread(target=run_bot_thread, args=(account_id,), daemon=True)
    thread.start()
    bot_threads[account_id] = thread
    
    return True, "Bot started successfully"

def stop_bot(account_id):
    """Stop the bot for a specific account"""
    global bot_status
    
    if account_id not in bot_status or not bot_status[account_id].get('running'):
        return False, "Bot is not running"
    
    bot_status[account_id]['running'] = False
    return True, "Bot stopped"

def start_all_bots():
    """Start bots for all accounts"""
    accounts = get_accounts()
    started = 0
    for account in accounts:
        if not account['status'].get('running'):
            success, _ = start_bot(account['id'])
            if success:
                started += 1
    return started

def stop_all_bots():
    """Stop all running bots"""
    stopped = 0
    for account_id in list(bot_status.keys()):
        if bot_status[account_id].get('running'):
            success, _ = stop_bot(account_id)
            if success:
                stopped += 1
    return stopped

# ======================== ROUTES ======================== #

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username, password = get_credentials()
        if request.form.get('username') == username and request.form.get('password') == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/accounts')
@login_required
def accounts_page():
    return render_template('accounts.html')

@app.route('/account/<account_id>')
@login_required
def account_detail(account_id):
    return render_template('account_detail.html', account_id=account_id)

@app.route('/account/<account_id>/settings')
@login_required
def account_settings(account_id):
    return render_template('account_settings.html', account_id=account_id)

@app.route('/logs')
@login_required
def logs_page():
    return render_template('logs.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

# ======================== API ENDPOINTS ======================== #

@app.route('/api/accounts')
@login_required
def api_accounts():
    return jsonify(get_accounts())

@app.route('/api/accounts/create', methods=['POST'])
@login_required
def api_create_account():
    data = request.json
    account_id = generate_account_id()
    
    config = {
        'ACCOUNT_NAME': data.get('name', 'New Account'),
        'OCI_REGION': data.get('region', 'eu-frankfurt-1'),
        'OCI_TENANCY_ID': data.get('tenancy_id', ''),
        'OCI_USER_ID': data.get('user_id', ''),
        'OCI_KEY_FINGERPRINT': data.get('fingerprint', ''),
        'OCI_PRIVATE_KEY_FILENAME': data.get('key_file', ''),
        'OCI_SUBNET_ID': data.get('subnet_id', ''),
        'OCI_AVAILABILITY_DOMAIN': data.get('availability_domain', ''),
        'OCI_SHAPE': data.get('shape', 'VM.Standard.A1.Flex'),
        'OCI_OCPUS': data.get('ocpus', '4'),
        'OCI_MEMORY_IN_GBS': data.get('memory', '24'),
        'OCI_IMAGE_ID': data.get('image_id', ''),
        'OCI_SSH_PUBLIC_KEY': data.get('ssh_key', ''),
        'OCI_DISPLAY_NAME': data.get('display_name', ''),
        'TELEGRAM_BOT_API_KEY': data.get('telegram_token', ''),
        'TELEGRAM_USER_ID': data.get('telegram_uid', ''),
        'OCI_RETRY_INTERVAL': data.get('retry_interval', '1'),
        'OCI_MIN_RETRY_INTERVAL': data.get('min_retry_interval', '1')
    }
    
    save_account_config(account_id, config)
    
    return jsonify({'success': True, 'account_id': account_id, 'message': 'Account created'})

@app.route('/api/accounts/<account_id>', methods=['GET', 'DELETE'])
@login_required
def api_account(account_id):
    if request.method == 'GET':
        config = get_account_config(account_id)
        if config:
            return jsonify(config)
        return jsonify({'error': 'Account not found'}), 404
    
    if request.method == 'DELETE':
        if delete_account(account_id):
            return jsonify({'success': True, 'message': 'Account deleted'})
        return jsonify({'success': False, 'message': 'Account not found'}), 404

@app.route('/api/accounts/<account_id>/settings', methods=['POST'])
@login_required
def api_account_settings(account_id):
    data = request.json
    save_account_config(account_id, data)
    return jsonify({'success': True, 'message': 'Settings saved'})

@app.route('/api/accounts/<account_id>/test')
@login_required
def api_test_account(account_id):
    success, data = test_oci_connection(account_id)
    return jsonify({'success': success, 'data': data})

@app.route('/api/accounts/<account_id>/instances')
@login_required
def api_account_instances(account_id):
    return jsonify(get_oci_instances(account_id))

@app.route('/api/accounts/<account_id>/storage')
@login_required
def api_account_storage(account_id):
    return jsonify(get_storage_info(account_id))

@app.route('/api/accounts/<account_id>/compute')
@login_required
def api_account_compute(account_id):
    return jsonify(get_compute_limits(account_id))

@app.route('/api/accounts/<account_id>/availability-domains')
@login_required
def api_account_ads(account_id):
    return jsonify(get_availability_domains(account_id))

@app.route('/api/accounts/<account_id>/bot/start', methods=['POST'])
@login_required
def api_account_bot_start(account_id):
    success, message = start_bot(account_id)
    return jsonify({
        'success': success,
        'message': message,
        'status': bot_status.get(account_id, {})
    })

@app.route('/api/accounts/<account_id>/bot/stop', methods=['POST'])
@login_required
def api_account_bot_stop(account_id):
    success, message = stop_bot(account_id)
    return jsonify({
        'success': success,
        'message': message,
        'status': bot_status.get(account_id, {})
    })

@app.route('/api/accounts/<account_id>/logs')
@login_required
def api_account_logs(account_id):
    return jsonify(logs_buffer.get(account_id, [])[-100:])

@app.route('/api/bot/start-all', methods=['POST'])
@login_required
def api_start_all():
    count = start_all_bots()
    return jsonify({'success': True, 'message': f'Started {count} bot(s)'})

@app.route('/api/bot/stop-all', methods=['POST'])
@login_required
def api_stop_all():
    count = stop_all_bots()
    return jsonify({'success': True, 'message': f'Stopped {count} bot(s)'})

@app.route('/api/status')
@login_required
def api_status():
    accounts = get_accounts()
    running_count = sum(1 for a in accounts if a['status'].get('running'))
    total_retries = sum(a['status'].get('retry_count', 0) for a in accounts)
    
    return jsonify({
        'accounts': len(accounts),
        'running': running_count,
        'total_retries': total_retries,
        'server_time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    })

@app.route('/api/logs')
@login_required
def api_all_logs():
    all_logs = []
    for account_id, logs in logs_buffer.items():
        all_logs.extend(logs[-50:])
    
    # Sort by timestamp
    all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify(all_logs[:100])

@app.route('/api/settings', methods=['GET', 'POST'])
@login_required
def api_settings():
    env_file = '.env'
    
    if request.method == 'GET':
        return jsonify({
            'WEB_USERNAME': os.getenv('WEB_USERNAME', 'admin'),
            'ACCOUNTS_DIR': os.getenv('ACCOUNTS_DIR', './accounts'),
            'WEB_PORT': os.getenv('WEB_PORT', '5000')
        })
    
    if request.method == 'POST':
        data = request.json
        
        try:
            for key, value in data.items():
                if key in ['WEB_USERNAME', 'WEB_PASSWORD', 'ACCOUNTS_DIR', 'SECRET_KEY']:
                    set_key(env_file, key, str(value))
                    os.environ[key] = str(value)
            
            return jsonify({'success': True, 'message': 'Settings saved'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

@app.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    accounts = get_accounts()
    running_bots = sum(1 for a in accounts if a['status'].get('running'))
    total_retries = sum(a['status'].get('retry_count', 0) for a in accounts)
    
    return jsonify({
        'total_accounts': len(accounts),
        'running_bots': running_bots,
        'total_retries': total_retries,
        'accounts': accounts
    })

# ======================== WEBSOCKET ======================== #

@socketio.on('connect', namespace='/logs')
def handle_connect():
    # Send all logs
    all_logs = []
    for account_id, logs in logs_buffer.items():
        all_logs.extend(logs[-20:])
    all_logs.sort(key=lambda x: x['timestamp'])
    
    emit('log_history', all_logs[-50:])
    emit('accounts_status', {aid: status for aid, status in bot_status.items()})

@socketio.on('subscribe', namespace='/logs')
def handle_subscribe(data):
    account_id = data.get('account_id')
    if account_id and account_id in logs_buffer:
        emit('log_history', logs_buffer[account_id][-50:])
        emit('bot_status', {'account_id': account_id, 'status': bot_status.get(account_id, {})})

# ======================== MAIN ======================== #

if __name__ == '__main__':
    # Create .env file if not exists
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write('WEB_USERNAME=admin\n')
            f.write('WEB_PASSWORD=admin123\n')
            f.write(f'SECRET_KEY={secrets.token_hex(32)}\n')
            f.write('ACCOUNTS_DIR=./accounts\n')
    
    port = int(os.getenv('WEB_PORT', 5000))
    host = os.getenv('WEB_HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting OCI Admin Panel on {host}:{port}")
    logger.info(f"Accounts directory: {ACCOUNTS_DIR}")
    
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
