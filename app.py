from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
import os
import json
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'

# Admin credentials (change in production)
app.config['ADMIN_USERNAME'] = 'admin'
app.config['ADMIN_PASSWORD'] = '1234'

# สร้างโฟลเดอร์สำหรับเก็บรูปภาพ
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images', 'products')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PROFILE_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images', 'profiles')
os.makedirs(PROFILE_FOLDER, exist_ok=True)

# ข้อมูลสินค้า
PRODUCTS = [
    {'id': 1, 'name': 'iPhone 15 Pro', 'price': 35999, 'category': 'อิเล็กทรอนิกส์', 'description': 'สมาร์ตโฟนรุ่นล่าสุด'},
    {'id': 2, 'name': 'Samsung 65" TV', 'price': 24999, 'category': 'อิเล็กทรอนิกส์', 'description': 'โทรทัศน์ 4K UltraHD'},
    {'id': 3, 'name': 'MacBook Pro M3', 'price': 59999, 'category': 'คอมพิวเตอร์', 'description': 'แล็ปท็อปสำหรับงานมืออาชีพ'},
    {'id': 4, 'name': 'Dell XPS 15', 'price': 44999, 'category': 'คอมพิวเตอร์', 'description': 'โน้ตบุ๊ค ยอดนิยมอันดับ 1'},
    {'id': 5, 'name': 'Canon EOS R5', 'price': 89999, 'category': 'กล้อง', 'description': 'กล้อง DSLR ระดับมืออาชีพ'},
    {'id': 6, 'name': 'Sony A7IV', 'price': 74999, 'category': 'กล้อง', 'description': 'กล้อง Mirrorless ที่ดีที่สุด'},
]

CATEGORIES = ['ทั้งหมด', 'อิเล็กทรอนิกส์', 'คอมพิวเตอร์', 'กล้อง']

# ในหน่วยความจำเก็บคำสั่งซื้อ (อ้างอิงเทส)
ORDERS = []

# ข้อมูลผู้ใช้ลูกค้า (เก็บในหน่วยความจำ)
USERS = []  # จะเติมบัญชีตัวอย่างหลังจากประกาศฟังก์ชันสร้าง avatar แล้ว

# ข้อมูล reviews/ratings (เก็บในหน่วยความจำ)
REVIEWS = []

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


# การตั้งค่าสำหรับอัพโหลดรูป
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def save_uploaded_image(file_storage, product_id):
    try:
        if not file_storage or file_storage.filename == '':
            return False
        if not allowed_file(file_storage.filename):
            return False

        # ใช้ Pillow แปลงเป็น PNG เสมอ เพื่อความเข้ากันกับเทมเพลต
        img = Image.open(file_storage.stream)
        image_path = os.path.join(UPLOAD_FOLDER, f'product_{product_id}.png')
        img = img.convert('RGBA') if img.mode in ('P', 'RGBA', 'LA') else img.convert('RGB')
        img.save(image_path, format='PNG')
        return True
    except Exception:
        return False

def generate_product_images():
    """สร้างรูปภาพสินค้า 6 รูปอัตโนมัติ"""
    colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1',
        '#FFA07A', '#98D8C8', '#F7DC6F'
    ]
    
    for idx, product in enumerate(PRODUCTS):
        image_path = os.path.join(UPLOAD_FOLDER, f'product_{product["id"]}.png')
        
        # ถ้ายังไม่มีรูป ให้สร้างใหม่
        if not os.path.exists(image_path):
            # สร้างรูปขนาด 400x400
            img = Image.new('RGB', (400, 400), color=colors[idx])
            draw = ImageDraw.Draw(img)
            
            # เขียนชื่อสินค้า
            try:
                font = ImageFont.truetype("arial.ttf", 28)
                price_font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
                price_font = ImageFont.load_default()
            
            # เขียนข้อความ
            text = product['name']
            price_text = f"฿{product['price']:,}"
            
            # หาตำแหน่งข้อความ
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (400 - text_width) // 2
            
            price_bbox = draw.textbbox((0, 0), price_text, font=price_font)
            price_width = price_bbox[2] - price_bbox[0]
            price_x = (400 - price_width) // 2
            
            # วาดข้อความ
            draw.text((text_x, 140), text, fill='white', font=font)
            draw.text((price_x, 240), price_text, fill='#FFD700', font=price_font)
            
            # บันทึกรูป
            img.save(image_path)

    # สร้างแบนเนอร์หลายภาพสำหรับแสดงเป็นสไลเดอร์พร้อมไล่สี (ถ้ายังไม่มี)
    banners = [
        {'idx': 1, 'colors': ['#667eea', '#764ba2'], 'text': '🛍️ ดีลพิเศษ - อิเล็กทรอนิกส์ลดราคา', 'subtitle': 'ลด 50% เฉพาะวันนี้!'},
        {'idx': 2, 'colors': ['#f093fb', '#f5576c'], 'text': '💻 โน้ตบุ๊คเรือธงประหยัดสุด', 'subtitle': 'MacBook & Dell พร้อมจัดส่ง 24 ชั่วโมง'},
        {'idx': 3, 'colors': ['#4facfe', '#00f2fe'], 'text': '📷 กล้องมืออาชีพเลือกได้', 'subtitle': 'Canon EOS R5 และ Sony A7IV ในราคาดี'},
    ]
    for banner in banners:
        banner_path = os.path.join(os.path.dirname(__file__), 'static', 'images', f'banner_{banner["idx"]}.png')
        if not os.path.exists(banner_path):
            try:
                bimg = Image.new('RGB', (1200, 350), color=banner['colors'][0])
                bdraw = ImageDraw.Draw(bimg)
                try:
                    title_font = ImageFont.truetype("arial.ttf", 56)
                    subtitle_font = ImageFont.truetype("arial.ttf", 28)
                except:
                    title_font = ImageFont.load_default()
                    subtitle_font = ImageFont.load_default()
                # วาดข้อความหลัก
                title = banner['text']
                bbox = bdraw.textbbox((0,0), title, font=title_font)
                w = bbox[2] - bbox[0]
                text_x = (1200 - w) // 2
                text_y = 80
                bdraw.text((text_x, text_y), title, fill='white', font=title_font)
                # วาดข้อความรอง
                subtitle = banner['subtitle']
                bbox_sub = bdraw.textbbox((0,0), subtitle, font=subtitle_font)
                w_sub = bbox_sub[2] - bbox_sub[0]
                sub_x = (1200 - w_sub) // 2
                bdraw.text((sub_x, 190), subtitle, fill='#ffffcc', font=subtitle_font)
                bimg.save(banner_path)
            except Exception:
                pass

def generate_anime_avatar(user_id, user_name):
    """สร้างรูปโปรไฟล์อนิเมะสำหรับผู้ใช้"""
    anime_styles = [
        {'colors': ['#FF9FF3', '#F368E0'], 'emoji': '👩‍🎨'},  # สีชมพู
        {'colors': ['#A29BFE', '#6C5CE7'], 'emoji': '👩'},     # สีม่วง
        {'colors': ['#74B9FF', '#0984E3'], 'emoji': '👨‍💻'},    # สีฟ้า
        {'colors': ['#55EFC4', '#00B894'], 'emoji': '🧚'},     # สีเขียว
        {'colors': ['#FDCB6E', '#F39C12'], 'emoji': '👯'},     # สีเหลือง
        {'colors': ['#FF7675', '#D63031'], 'emoji': '⛩️'},     # สีแดง
        {'colors': ['#FD79A8', '#E84393'], 'emoji': '💕'},     # สีชมพูแบบสดใส
        {'colors': ['#81ECEC', '#00CEC9'], 'emoji': '👽'},     # สีฟ้าอมเขียว
    ]
    
    # เลือก style จาก user_id
    style = anime_styles[user_id % len(anime_styles)]
    
    # สร้างรูปภาพขนาด 200x200
    avatar_img = Image.new('RGB', (200, 200), color=style['colors'][0])
    draw = ImageDraw.Draw(avatar_img)
    
    # วาดพื้นหลัง gradient (ทำแบบง่ายด้วย rectangles)
    for i in range(200):
        ratio = i / 200
        # สมมติ interpolate ระหว่าง 2 สี
        r = int(int(style['colors'][0][1:3], 16) * (1-ratio) + int(style['colors'][1][1:3], 16) * ratio)
        g = int(int(style['colors'][0][3:5], 16) * (1-ratio) + int(style['colors'][1][3:5], 16) * ratio)
        b = int(int(style['colors'][0][5:7], 16) * (1-ratio) + int(style['colors'][1][5:7], 16) * ratio)
        color = f'#{r:02x}{g:02x}{b:02x}'
        draw.line([(0, i), (200, i)], fill=color, width=1)
    
    # เขียน emoji ตรงกลาง
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        font = ImageFont.load_default()
    
    # หา emoji จาก user_name
    emojis = ['🤖', '⚡', '🌟', '✨', '💎', '🎮', '🚀', '🎯']
    emoji = emojis[user_id % len(emojis)]
    
    # วาด emoji ตรงกลาง
    bbox = draw.textbbox((0, 0), emoji, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (200 - text_width) // 2
    y = (200 - text_height) // 2
    draw.text((x, y), emoji, font=font, fill='white')
    
    # บันทึกรูปภาพ
    avatar_path = os.path.join(PROFILE_FOLDER, f'profile_{user_id}.png')
    avatar_img.save(avatar_path)
    return f'profile_{user_id}.png'


# สร้างบัญชีตัวอย่างให้เข้าทดสอบได้ทันทีหลังฟังก์ชันถูกประกาศ
if not USERS:
    USERS.append({
        'id': 1,
        'email': 'user@example.com',
        'password': 'password',
        'name': 'Demo User',
        'profile_pic': generate_anime_avatar(1, 'Demo User')
    })

def get_cart_total(cart):
    """คำนวณยอดรวมของตะกร้า"""
    total = 0
    for item in cart:
        product = next((p for p in PRODUCTS if p['id'] == item['product_id']), None)
        if product:
            total += product['price'] * item['quantity']
    return total

@app.route('/')
def index():
    """หน้าแรก - แสดงสินค้าทั้งหมด"""
    category = request.args.get('category', 'ทั้งหมด')
    
    # กรองสินค้าตามหมวดหมู่
    if category == 'ทั้งหมด':
        filtered_products = PRODUCTS
    else:
        filtered_products = [p for p in PRODUCTS if p['category'] == category]
    
    cart_count = len(session.get('cart', []))
    
    return render_template('index.html', 
                         products=filtered_products,
                         categories=CATEGORIES,
                         current_category=category,
                         cart_count=cart_count)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """หน้ารายละเอียดสินค้า"""
    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not product:
        return redirect(url_for('index'))
    
    # สินค้าที่เกี่ยวข้อง (หมวดเดียวกัน ลบออกตัวเอง)
    related = [p for p in PRODUCTS if p['category'] == product['category'] and p['id'] != product_id]
    
    # ดึง reviews ของสินค้านี้
    product_reviews = [r for r in REVIEWS if r['product_id'] == product_id]
    
    cart_count = len(session.get('cart', []))
    
    return render_template('product_detail.html', 
                         product=product,
                         related=related,
                         reviews=product_reviews,
                         cart_count=cart_count)

@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    """เพิ่มสินค้าลงตะกร้า"""
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    if 'cart' not in session:
        session['cart'] = []
    
    # ตรวจสอบว่าสินค้านี้มีในตะกร้าแล้วหรือไม่
    cart = session['cart']
    existing_item = next((item for item in cart if item['product_id'] == product_id), None)
    
    if existing_item:
        existing_item['quantity'] += quantity
    else:
        cart.append({'product_id': product_id, 'quantity': quantity})
    
    session.modified = True
    
    return jsonify({
        'success': True,
        'cart_count': len(cart),
        'message': 'เพิ่มสินค้าลงตะกร้าแล้ว'
    })

@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    """ลบสินค้าออกจากตะกร้า"""
    data = request.json
    product_id = data.get('product_id')
    
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['product_id'] != product_id]
        session.modified = True
    
    return jsonify({'success': True})

@app.route('/api/cart/update', methods=['POST'])
def update_cart():
    """อัปเดตจำนวนสินค้าในตะกร้า"""
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity')
    
    if 'cart' in session:
        item = next((item for item in session['cart'] if item['product_id'] == product_id), None)
        if item:
            if quantity <= 0:
                session['cart'] = [i for i in session['cart'] if i['product_id'] != product_id]
            else:
                item['quantity'] = quantity
            session.modified = True
    
    return jsonify({'success': True})

@app.route('/cart')
def cart():
    """หน้าตะกร้าสินค้า"""
    cart = session.get('cart', [])
    cart_items = []
    
    for item in cart:
        product = next((p for p in PRODUCTS if p['id'] == item['product_id']), None)
        if product:
            cart_items.append({
                **product,
                'quantity': item['quantity'],
                'total': product['price'] * item['quantity']
            })
    
    subtotal = sum(item['total'] for item in cart_items)
    shipping = 50 if subtotal > 0 else 0
    tax = subtotal * 0.07  # 7% VAT
    total = subtotal + shipping + tax
    
    return render_template('cart.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         shipping=shipping,
                         tax=tax,
                         total=total)

@app.route('/checkout')
def checkout():
    """หน้าชำระเงิน"""
    cart = session.get('cart', [])
    cart_items = []
    
    for item in cart:
        product = next((p for p in PRODUCTS if p['id'] == item['product_id']), None)
        if product:
            cart_items.append({
                **product,
                'quantity': item['quantity'],
                'total': product['price'] * item['quantity']
            })
    
    subtotal = sum(item['total'] for item in cart_items)
    shipping = 50 if subtotal > 0 else 0
    tax = subtotal * 0.07
    total = subtotal + shipping + tax
    
    return render_template('checkout.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         shipping=shipping,
                         tax=tax,
                         total=total)

@app.route('/api/order/place', methods=['POST'])
def place_order():
    """ยืนยันคำสั่งซื้อ"""
    data = request.json
    
    # บันทึกข้อมูลคำสั่งซื้อ
    order_data = {
        'order_id': f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'customer': data,
        'cart': session.get('cart', []),
        'created_at': datetime.now().isoformat(),
        'status': 'Pending',          # สถานะเริ่มต้น
        'tracking_number': ''         # รหัสติดตาม (ถ้ามี)
    }
    # ถ้าผู้ใช้ล็อกอิน ให้เก็บ user_id ด้วย
    if session.get('user_id'):
        order_data['user_id'] = session.get('user_id')
    
    # ล้างตะกร้า
    if 'cart' in session:
        session['cart'] = []
        session.modified = True
    # เก็บคำสั่งซื้อในหน่วยความจำ (ตัวอย่าง)
    ORDERS.append(order_data)

    return jsonify({
        'success': True,
        'order_id': order_data['order_id'],
        'message': 'สั่งซื้อสำเร็จ'
    })

@app.route('/success/<order_id>')
def order_success(order_id):
    """หน้าการสั่งซื้อสำเร็จ"""
    order = next((o for o in ORDERS if o.get('order_id') == order_id), None)
    status = order.get('status') if order else ''
    tracking = order.get('tracking_number') if order else ''
    return render_template('success.html', order_id=order_id, status=status, tracking=tracking)


# --- Customer Auth Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        # ตรวจสอบว่า email ซ้ำแล้วหรือไม่
        if any(u['email'] == email for u in USERS):
            error = 'อีเมลนี้ลงทะเบียนไปแล้ว'
        elif not email or not password or not name:
            error = 'กรุณากรอกข้อมูลให้ครบถ้วน'
        else:
            # สร้างบัญชีใหม่
            user_id = len(USERS) + 1
            # สร้างรูปโปรไฟล์อนิเมะ
            profile_pic = generate_anime_avatar(user_id, name)
            USERS.append({'id': user_id, 'email': email, 'password': password, 'name': name, 'profile_pic': profile_pic})
            session['user_id'] = user_id
            session['user_name'] = name
            return redirect(url_for('index'))
    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = next((u for u in USERS if u['email'] == email and u['password'] == password), None)
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(request.args.get('next', url_for('index')))
        else:
            error = 'อีเมลหรือรหัสผ่านไม่ถูกต้อง'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    user = next((u for u in USERS if u['id'] == session.get('user_id')), None)
    if not user:
        return redirect(url_for('login'))
    
    # ถ้าผู้ใช้ไม่มี profile_pic ให้สร้างให้
    if 'profile_pic' not in user:
        profile_pic = generate_anime_avatar(user['id'], user['name'])
        user['profile_pic'] = profile_pic
    
    # ดึง orders ของผู้ใช้นี้ (หากเก็บ user_id ใน order ด้วย)
    my_reviews = [r for r in REVIEWS if r.get('user_id') == user['id']]
    my_orders = [o for o in ORDERS if o.get('user_id') == user['id']]
    
    return render_template('profile.html', user=user, reviews=my_reviews, orders=my_orders)


# --- Review Routes ---
@app.route('/product/<int:product_id>/review', methods=['GET', 'POST'])
@login_required
def add_review(product_id):
    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not product:
        return redirect(url_for('index'))
    
    user = next((u for u in USERS if u['id'] == session.get('user_id')), None)
    error = None
    
    if request.method == 'POST':
        rating = request.form.get('rating', '5')
        comment = request.form.get('comment', '')
        
        try:
            rating = int(rating)
            if 1 <= rating <= 5 and len(comment) > 0:
                review_id = len(REVIEWS) + 1
                REVIEWS.append({
                    'id': review_id,
                    'product_id': product_id,
                    'user_id': user['id'],
                    'user_name': user['name'],
                    'rating': rating,
                    'comment': comment,
                    'created_at': datetime.now().isoformat()
                })
                return redirect(url_for('product_detail', product_id=product_id))
            else:
                error = 'กรุณากรอกคะแนนและความเห็นให้ครบถ้วน'
        except ValueError:
            error = 'คะแนนไม่ถูกต้อง'
    
    return render_template('review_form.html', product=product, user=user, error=error)


@app.route('/api/product/<int:product_id>/reviews')
def get_reviews(product_id):
    """API เพื่อดึง reviews ของสินค้า"""
    reviews = [r for r in REVIEWS if r['product_id'] == product_id]
    return jsonify(reviews)


# --- Admin routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'
    return render_template('admin_login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', products=PRODUCTS, orders=ORDERS)


@app.route('/admin/order/update/<order_id>', methods=['POST'])
@admin_required
def admin_order_update(order_id):
    """Allow admin to change status or tracking number of an order."""
    status = request.form.get('status')
    tracking = request.form.get('tracking')
    for o in ORDERS:
        if o.get('order_id') == order_id:
            if status:
                o['status'] = status
            if tracking is not None:
                o['tracking_number'] = tracking
            break
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/products')
@admin_required
def admin_products():
    return render_template('admin_products.html', products=PRODUCTS)


# --- Admin banner management ---
@app.route('/admin/banner', methods=['GET', 'POST'])
@admin_required
def admin_banner():
    """Allow admin to upload or replace the front anime banner."""
    message = None
    banner_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'anime_front.png')
    if request.method == 'POST':
        file = request.files.get('banner')
        if file and file.filename and allowed_file(file.filename):
            try:
                # save directly with png format
                img = Image.open(file.stream)
                img = img.convert('RGB')
                img.save(banner_path, format='PNG')
                message = 'อัปโหลดรูปสำเร็จ'
            except Exception:
                message = 'เกิดข้อผิดพลาดขณะบันทึกรูป'
        else:
            message = 'ไฟล์ไม่ถูกต้อง (รองรับ PNG,JPG,JPEG,GIF)'
    # check if banner exists to show preview
    banner_exists = os.path.exists(banner_path)
    return render_template('admin_banner.html', message=message, banner_exists=banner_exists)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_products_add():
    if request.method == 'POST':
        name = request.form.get('name')
        price = int(request.form.get('price') or 0)
        category = request.form.get('category')
        description = request.form.get('description')
        new_id = max((p['id'] for p in PRODUCTS), default=0) + 1
        PRODUCTS.append({'id': new_id, 'name': name, 'price': price, 'category': category, 'description': description})

        # ถ้ามีไฟล์รูปที่อัพโหลด ให้บันทึกเป็น product_{id}.png
        image = request.files.get('image')
        saved = False
        if image and image.filename:
            saved = save_uploaded_image(image, new_id)

        # ถ้าไม่มีรูปที่อัพโหลด ให้สร้างรูปตัวอย่างอัตโนมัติ
        if not saved:
            generate_product_images()

        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=None, categories=CATEGORIES)


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_products_edit(product_id):
    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not product:
        return redirect(url_for('admin_products'))
    if request.method == 'POST':
        product['name'] = request.form.get('name')
        product['price'] = int(request.form.get('price') or 0)
        product['category'] = request.form.get('category')
        product['description'] = request.form.get('description')
        # ถ้ามีไฟล์รูปที่อัพโหลด ให้บันทึกทับรูปเดิม
        image = request.files.get('image')
        saved = False
        if image and image.filename:
            saved = save_uploaded_image(image, product_id)

        # ถ้าไม่มีรูปอัพโหลด ให้สร้างรูปตัวอย่าง (ถ้ายังไม่มี)
        if not saved:
            generate_product_images()

        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=product, categories=CATEGORIES)


@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_products_delete(product_id):
    global PRODUCTS
    PRODUCTS = [p for p in PRODUCTS if p['id'] != product_id]
    # ลบไฟล์รูปถ้ามี
    try:
        image_path = os.path.join(UPLOAD_FOLDER, f'product_{product_id}.png')
        if os.path.exists(image_path):
            os.remove(image_path)
    except Exception:
        pass
    return redirect(url_for('admin_products'))

def ensure_default_logo():
    """Create a simple placeholder logo if none exists."""
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'logo.png')
    if not os.path.exists(logo_path):
        try:
            img = Image.new('RGB', (80, 80), color='#00d4ff')
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 36)
            except:
                font = ImageFont.load_default()
            text = "SM"
            bbox = draw.textbbox((0,0), text, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            draw.text(((80-w)//2, (80-h)//2), text, fill='white', font=font)
            img.save(logo_path, format='PNG')
        except Exception:
            pass


if __name__ == '__main__':
    # สร้างรูปภาพสินค้า
    generate_product_images()
    # สร้างโลโก้เริ่มต้นหากยังไม่มี
    ensure_default_logo()
    
    # รันแอพพลิเคชัน
    app.run(debug=True, host='localhost', port=5000)
