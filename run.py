from app import app, generate_product_images


if __name__ == '__main__':
    # สร้างรูปสินค้าก่อนรัน (ถ้ายังไม่มี)
    generate_product_images()
    app.run(debug=True, host='localhost', port=5000)
