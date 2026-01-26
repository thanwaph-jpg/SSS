from flask import Flask, render_template, request, jsonify, session
from PIL import Image, ImageDraw, ImageFont
import os
import json
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'

# สร้างโฟลเดอร์สำหรับเก็บรูปภาพ
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images', 'products')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        'created_at': datetime.now().isoformat()
    }
    
    # ล้างตะกร้า
    if 'cart' in session:
        session['cart'] = []
        session.modified = True
    
    return jsonify({
        'success': True,
        'order_id': order_data['order_id'],
        'message': 'สั่งซื้อสำเร็จ'
    })

@app.route('/success/<order_id>')
def order_success(order_id):
    """หน้าการสั่งซื้อสำเร็จ"""
    return render_template('success.html', order_id=order_id)

if __name__ == '__main__':
    # สร้างรูปภาพสินค้า
    generate_product_images()
    
    # รันแอพพลิเคชัน
    app.run(debug=True, host='localhost', port=5000)
