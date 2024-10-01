from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from firebase_admin import firestore, credentials, auth, db
import firebase_admin
import uuid
from functools import wraps  # Import wraps for the login_required decorator

app = Flask(__name__)
app.secret_key = '1234'  # Replace this with a secure secret key

# Initialize Firebase Admin SDK
cred = credentials.Certificate('config/iakretail7-firebase-adminsdk-fiaat-9ceeeef7f0.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://iakretail7-default-rtdb.firebaseio.com/'
})

# Initialize Firestore
firestore_db = firestore.client()

# Function to check if user is logged in (can be modified further)
def login_required(f):
    @wraps(f)  # Use wraps to preserve function metadata
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Route for login page
@app.route('/', methods=['GET'])
def login():
    return render_template('login.html')

# Set session route (for setting user session after login)
@app.route('/set_session', methods=['POST'])
def set_session():
    data = request.get_json()
    session['user'] = data['email']
    return '', 204

# Route for the dashboard page
@app.route('/beranda', methods=['GET', 'POST'])
@login_required
def beranda():
    return render_template('beranda.html')

# Route to handle logout
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Route to handle user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = auth.create_user(email=email, password=password)
            flash("Account successfully created!", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(str(e), "danger")
    return render_template('register.html')

@app.route('/transaksi', methods=['GET'])
@login_required
def transaksi():
    try:
        # Fetch all documents from the 'transaksi' collection
        transaksi_items = []
        docs = firestore_db.collection('transaksi').stream()

        for doc in docs:
            item = doc.to_dict()  # Convert Firestore document to a dictionary
            transaksi_items.append({
                'name': doc.id,  # Product name from Firestore document ID
                'description': item.get('Deskripsi', 'No description available'),
                'price': item.get('Harga', 0),
                'stock': item.get('Stok', 0)  # Fetching product stock
            })

        # Pass the retrieved products to the template
        return render_template('transaksi.html', products=transaksi_items)

    except Exception as e:
        print(f"Error fetching data: {e}")
        return jsonify({'error': str(e)})

@app.route('/gudang', methods=['GET'])
@login_required
def gudang():
    try:
        inventory_items = []
        docs = firestore_db.collection('gudang').stream()

        for doc in docs:
            item = doc.to_dict()
            inventory_items.append(item)

        return render_template('gudang.html', inventory_items=inventory_items)

    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('gudang'))

# Route to add a new inventory item to the Firebase Realtime Database
@app.route('/add_inventory', methods=['POST'])
@login_required
def add_inventory():
    nama = request.form.get('nama')
    stok = request.form.get('stok')

    if not nama or not stok:
        flash("Nama dan stok tidak boleh kosong", "danger")
        return redirect(url_for('gudang'))

    try:
        # Generate a unique ID for the document
        doc_ref = firestore_db.collection('gudang').document()
        doc_ref.set({
            'id_barang': str(uuid.uuid4()),  # Unique ID for the item
            'nama_barang': nama,
            'stok': int(stok)
        })
        flash("Item berhasil ditambahkan!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for('gudang'))

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    try:
        # Get the cart data from the POST request
        cart_data = request.json.get('cart', [])

        if not cart_data:
            return jsonify({'error': 'Keranjang kosong'}), 400

        # Iterate through each item in the cart and store them in Firestore 'pesan' collection
        for item in cart_data:
            # Generate a unique ID for each item in the cart
            pesan_id = str(uuid.uuid4())

            # Prepare the data to be saved in Firestore
            pesan_data = {
                'id_barang': pesan_id,
                'nama_barang': item['name'],
                'distributor': item['distributor'],
                'quantity': item['quantity'],
                'harga': item['totalPrice'],
                'status': 'ordered'
            }

            # Save each item to the Firestore 'pesan' collection
            firestore_db.collection('pesan').document(pesan_id).set(pesan_data)

        return jsonify({'message': 'Checkout successful!'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/lacak_pesanan', methods=['GET'])
@login_required
def lacak_pesanan():
    # Fetch the data from Firestore
    orders_ref = firestore_db.collection('lacak_pesanan').stream()
    print(orders_ref)
    orders = []

    for doc in orders_ref:
        order_data = doc.to_dict()

        # Convert Firestore Timestamp to a readable format
        order_date = order_data.get('order_date')
        if order_date:  # Check if the field exists
            order_date = order_date.strftime("%Y-%m-%d %H:%M:%S")  # Convert Firestore Timestamp to string

        orders.append({
            'id_resi': order_data.get('id_resi'),
            'order_date': order_data.get('order_date'),
            'distributor': order_data.get('distributor'),
            'nama_barang': order_data.get('nama_barang'),
            'harga': order_data.get('harga'),
            'lama_pengiriman': order_data.get('lama_pengiriman'),
            'status': order_data.get('status')
        })

    # Pass the orders to the template
    return render_template('lacak_pesanan.html', orders=orders)


@app.route('/histori', methods=['GET'])
@login_required
def histori():
    try:
        # Fetch documents from the 'histori' collection in Firestore (assuming it exists)
        histori_items = []
        docs = firestore_db.collection('histori').stream()

        for doc in docs:
            item = doc.to_dict()  # Convert Firestore document to a dictionary
            histori_items.append({
                'id': doc.id,  # Use document ID as the transaction ID
                'item': item.get('Item', 'No item available'),
                'time': item.get('Waktu', 'No time available'),
                'quantity': item.get('Jumlah', 0),
                'price': item.get('Harga', 0),
            })

        # Pass the items to the 'histori.html' template
        return render_template('histori.html', transactions=histori_items)
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('beranda'))

# New route for pesan page
@app.route('/pesan', methods=['GET'])
@login_required
def pesan():
    try:
        # Ambil semua dokumen dari koleksi 'pesan'
        pesan_items = []
        docs = firestore_db.collection('pesan').stream()  # Stream dokumen dari koleksi

        # Iterasi dokumen yang diambil
        for doc in docs:
            item = doc.to_dict()  # Konversi dokumen Firestore menjadi dictionary
            pesan_items.append({
                'id_barang': item.get('id_barang', 'No ID available'),
                'nama_barang': item.get('nama_barang', 'No name available'),
                'berat': item.get('berat', 0),
                'stok': item.get('stok', 0),
                'harga': item.get('harga', 0)  # Include 'harga' field (updated field name)
            })

        # Kirim data yang diambil ke template pesan.html
        return render_template('pesan.html', items=pesan_items)

    except Exception as e:
        flash(f"Error fetching data: {str(e)}", "danger")
        return redirect(url_for('beranda'))



@app.route('/delete_item/<item_id>', methods=['POST'])
def delete_item(item_id):
    # Query the Firestore database to delete the item by its ID
    try:
        db.collection('gudang').document(item_id).delete()  # 'gudang' is the collection name
        print(f"Item {item_id} has been deleted")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    # Redirect back to the inventory list
    return redirect(url_for('gudang'))

@app.route('/calculate_price', methods=['POST'])
@login_required
def calculate_price():
    data = request.get_json()
    quantity = data['quantity']
    unit_price = data['unitPrice']
    total_price = quantity * unit_price
    return jsonify({'total_price': total_price})

# @app.route('/histori', methods=['GET'])
# def histori():
#     return render_template('histori.html')


if __name__ == '__main__':
    app.run(debug=True)
