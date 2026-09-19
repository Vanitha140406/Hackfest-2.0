"""
Campus Bites - Indian College Canteen Pre-Ordering & Smart Queue System
A modern Flask + SQLite web application for college canteens.
Designed for college hackathon demonstrations and campus student use.
"""

from datetime import datetime, date
import io
import base64

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    abort,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
import qrcode

# ====================================================================
# STEP 1: Flask Application Setup
# ====================================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'campus_bites_hackathon_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access your canteen orders and cart.'
login_manager.login_message_category = 'info'


# ====================================================================
# STEP 2: Database Models (SQLite)
# ====================================================================
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), default='')
    phone = db.Column(db.String(20), default='')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    orders = db.relationship('Order', backref='student', lazy=True)


class FoodItem(db.Model):
    __tablename__ = 'food_item'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Meals, Snacks, Fast Food, Desserts, Beverages
    description = db.Column(db.String(255), default='')
    price = db.Column(db.Float, nullable=False)  # Stored in INR (₹)
    image = db.Column(db.String(100), default='samosa.jpg')
    available = db.Column(db.Boolean, default=True)
    order_count = db.Column(db.Integer, default=0)


class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token_number = db.Column(db.String(20), unique=True, nullable=False)  # e.g. #A101
    student_name = db.Column(db.String(100), default='')
    student_phone = db.Column(db.String(20), default='')
    pickup_time = db.Column(db.String(50), default='ASAP')
    payment_method = db.Column(db.String(50), default='Pay at Canteen Counter')
    items_summary = db.Column(db.Text, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Pending')  # Pending, Preparing, Ready, Completed
    created_at = db.Column(db.DateTime, default=datetime.now)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey('food_item.id'), nullable=False)
    food_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)


class SpecialOffer(db.Model):
    __tablename__ = 'special_offer'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


# ====================================================================
# HELPER FUNCTIONS: Queue Calculation & QR Code Generation
# ====================================================================
def get_queue_info(order):
    """
    Calculates queue position and estimated waiting time.
    Formula: 3 minutes per active order ahead in queue.
    """
    if order.status in ['Pending', 'Preparing']:
        orders_ahead = Order.query.filter(
            Order.status.in_(['Pending', 'Preparing']),
            Order.id < order.id
        ).count()
        queue_position = orders_ahead + 1
        waiting_time = queue_position * 3
    else:
        orders_ahead = 0
        queue_position = 0
        waiting_time = 0
    return queue_position, orders_ahead, waiting_time


def generate_qr_base64(data_text):
    """Generates a base64 encoded PNG QR code for counter scanning."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4,
            border=2,
        )
        qr.add_data(data_text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception:
        return None


def generate_next_token():
    """Generates sequential token numbers formatted like #A101, #A102..."""
    last_order = Order.query.order_by(Order.id.desc()).first()
    if last_order and last_order.token_number and last_order.token_number.startswith('#A'):
        try:
            num = int(last_order.token_number.replace('#A', ''))
            return f"#A{num + 1}"
        except ValueError:
            return f"#A{100 + last_order.id + 1}"
    return "#A101"


# ====================================================================
# STEP 3: Student Registration & Authentication
# ====================================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('menu'))

    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()

        if User.query.filter_by(username=username).first():
            flash('This Roll No. or username is already registered! Please log in.', 'danger')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        # Note: Normal student registration strictly creates is_admin=False
        new_student = User(
            username=username,
            password=hashed_pw,
            full_name=full_name,
            phone=phone,
            is_admin=False
        )
        db.session.add(new_student)
        db.session.commit()

        flash('Registration successful! Please log in with your credentials.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('menu'))

    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            next_page = request.args.get('next')
            if user.is_admin:
                return redirect(next_page or url_for('admin_dashboard'))
            return redirect(next_page or url_for('menu'))

        flash('Invalid username or password. Please check your credentials.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('menu'))


# ====================================================================
# STEP 4: Indian Food Menu, Search, & Live Status
# ====================================================================
@app.route('/')
@app.route('/menu')
def menu():
    # Active kitchen load metrics
    active_orders_count = Order.query.filter(Order.status.in_(['Pending', 'Preparing'])).count()
    avg_wait_time = max(active_orders_count * 3, 5) if active_orders_count > 0 else 5

    # Top popular items (calculated from order_count)
    popular_items = FoodItem.query.order_by(FoodItem.order_count.desc(), FoodItem.id.asc()).limit(4).all()

    # Active Special offer
    special_offer = SpecialOffer.query.filter_by(active=True).first()

    # Full food catalog
    items = FoodItem.query.order_by(FoodItem.category.asc(), FoodItem.name.asc()).all()

    return render_template(
        'menu.html',
        items=items,
        popular_items=popular_items,
        special_offer=special_offer,
        active_orders_count=active_orders_count,
        avg_wait_time=avg_wait_time
    )


# ====================================================================
# STEP 5: Food Cart Management (+ / - / Remove / Clear)
# ====================================================================
@app.route('/add_to_cart/<int:item_id>')
@login_required
def add_to_cart(item_id):
    food = db.session.get(FoodItem, item_id)
    if not food:
        flash('Food item not found!', 'danger')
        return redirect(url_for('menu'))

    if not food.available:
        flash(f'Sorry, {food.name} is currently OUT OF STOCK!', 'warning')
        return redirect(url_for('menu'))

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']
    cart[str(item_id)] = cart.get(str(item_id), 0) + 1
    session.modified = True

    flash(f'{food.name} added to cart!', 'success')
    return redirect(url_for('menu'))


@app.route('/cart')
@login_required
def cart():
    cart_data = session.get('cart', {})
    items = []
    total = 0
    total_qty = 0

    for item_id_str, qty in list(cart_data.items()):
        food = db.session.get(FoodItem, int(item_id_str))
        if food:
            subtotal = food.price * qty
            total += subtotal
            total_qty += qty
            items.append({
                'food': food,
                'qty': qty,
                'subtotal': subtotal
            })

    return render_template('cart.html', items=items, total=total, total_qty=total_qty)


@app.route('/cart/update/<int:item_id>/<action>')
@login_required
def update_cart(item_id, action):
    if 'cart' not in session:
        return redirect(url_for('cart'))

    cart = session['cart']
    key = str(item_id)

    if key in cart:
        if action == 'increase':
            cart[key] += 1
        elif action == 'decrease':
            cart[key] -= 1
            if cart[key] <= 0:
                del cart[key]
        elif action == 'remove':
            del cart[key]

    session.modified = True
    return redirect(url_for('cart'))


@app.route('/cart/clear')
@login_required
def clear_cart():
    session.pop('cart', None)
    flash('Your cart has been cleared.', 'info')
    return redirect(url_for('cart'))


# ====================================================================
# STEP 6: Checkout, Token Generation & Queue Entry
# ====================================================================
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_data = session.get('cart', {})
    if not cart_data:
        flash('Your cart is empty! Please select food items first.', 'warning')
        return redirect(url_for('menu'))

    items = []
    total = 0
    total_qty = 0

    for item_id_str, qty in cart_data.items():
        food = db.session.get(FoodItem, int(item_id_str))
        if food and food.available:
            subtotal = food.price * qty
            total += subtotal
            total_qty += qty
            items.append({
                'food': food,
                'qty': qty,
                'subtotal': subtotal
            })

    if not items:
        session.pop('cart', None)
        flash('The items in your cart are currently unavailable.', 'warning')
        return redirect(url_for('menu'))

    if request.method == 'POST':
        student_name = request.form.get('student_name', current_user.full_name or current_user.username)
        student_phone = request.form.get('phone', current_user.phone or '')
        pickup_time = request.form.get('pickup_time', 'ASAP')

        token = generate_next_token()
        summary_parts = [f"{entry['food'].name} × {entry['qty']}" for entry in items]

        new_order = Order(
            user_id=current_user.id,
            token_number=token,
            student_name=student_name,
            student_phone=student_phone,
            pickup_time=pickup_time,
            payment_method='Pay at Canteen Counter',
            items_summary=", ".join(summary_parts),
            total_price=total,
            status='Pending'
        )
        db.session.add(new_order)
        db.session.flush()  # assign new_order.id

        # Insert detailed OrderItems and increment order count for popularity calculation
        for entry in items:
            order_item = OrderItem(
                order_id=new_order.id,
                food_id=entry['food'].id,
                food_name=entry['food'].name,
                quantity=entry['qty'],
                price=entry['food'].price,
                subtotal=entry['subtotal']
            )
            db.session.add(order_item)
            entry['food'].order_count += entry['qty']

        db.session.commit()

        # Clear active cart
        session.pop('cart', None)
        flash(f'🎉 Order Placed! Your Token is {token}.', 'success')
        return redirect(url_for('track_order', order_id=new_order.id))

    return render_template('checkout.html', items=items, total=total, total_qty=total_qty)


# ====================================================================
# STEP 7 & 8: Smart Queue Calculation & Live Order Tracking
# ====================================================================
@app.route('/track/<int:order_id>')
@login_required
def track_order(order_id):
    order = db.get_or_404(Order, order_id)

    # Permission check: Student can view their own order; Admins can view any order
    if not current_user.is_admin and order.user_id != current_user.id:
        flash('You do not have permission to view this order.', 'danger')
        return redirect(url_for('menu'))

    queue_position, orders_ahead, waiting_time = get_queue_info(order)

    # Generate QR Code pass
    qr_data = f"TOKEN:{order.token_number}|ID:{order.id}|NAME:{order.student_name}|TOTAL:Rs.{order.total_price}|STATUS:{order.status}"
    qr_code_b64 = generate_qr_base64(qr_data)

    return render_template(
        'track_order.html',
        order=order,
        queue_position=queue_position,
        orders_ahead=orders_ahead,
        waiting_time=waiting_time,
        qr_code_b64=qr_code_b64
    )


# ====================================================================
# STEP 9: Student Dashboard & Order History
# ====================================================================
@app.route('/dashboard')
@login_required
def dashboard():
    # Find current active order (if any)
    active_order = Order.query.filter(
        Order.user_id == current_user.id,
        Order.status.in_(['Pending', 'Preparing', 'Ready'])
    ).order_by(Order.id.desc()).first()

    queue_position, orders_ahead, waiting_time = (0, 0, 0)
    if active_order:
        queue_position, orders_ahead, waiting_time = get_queue_info(active_order)

    total_orders_count = Order.query.filter_by(user_id=current_user.id).count()
    recent_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        active_order=active_order,
        queue_position=queue_position,
        waiting_time=waiting_time,
        total_orders_count=total_orders_count,
        recent_orders=recent_orders
    )


@app.route('/orders')
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    return render_template('order_history.html', orders=orders)


# ====================================================================
# STEP 10: Admin Dashboard & Queue Management
# ====================================================================
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access Denied: Canteen Admin privileges required.', 'danger')
        return redirect(url_for('menu'))

    status_filter = request.args.get('status', 'all')
    all_orders = Order.query.order_by(Order.id.desc()).all()

    if status_filter in ['Pending', 'Preparing', 'Ready', 'Completed']:
        filtered_orders = [o for o in all_orders if o.status == status_filter]
    else:
        filtered_orders = all_orders

    # Analytics metrics
    today_date = date.today()
    today_orders = [o for o in all_orders if o.created_at.date() == today_date]
    today_revenue = sum(o.total_price for o in today_orders)

    pending_orders = sum(1 for o in all_orders if o.status == 'Pending')
    preparing_orders = sum(1 for o in all_orders if o.status == 'Preparing')
    ready_orders = sum(1 for o in all_orders if o.status == 'Ready')

    stats = {
        'today_orders': len(today_orders) if today_orders else len(all_orders),
        'today_revenue': today_revenue if today_revenue else sum(o.total_price for o in all_orders),
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
    }

    return render_template(
        'admin_dashboard.html',
        orders=all_orders,
        filtered_orders=filtered_orders,
        current_filter=status_filter,
        stats=stats
    )


@app.route('/admin/update/<int:order_id>/<status>')
@login_required
def update_status(order_id, status):
    if not current_user.is_admin:
        flash('Access Denied: Canteen Admin privileges required.', 'danger')
        return redirect(url_for('menu'))

    order = db.get_or_404(Order, order_id)
    if status in ['Pending', 'Preparing', 'Ready', 'Completed']:
        order.status = status
        db.session.commit()
        flash(f'Token {order.token_number} status updated to "{status}".', 'success')

    return redirect(url_for('admin_dashboard'))


# ====================================================================
# STEP 11: Food Management for Admin (CRUD + Stock Availability)
# ====================================================================
@app.route('/admin/food')
@login_required
def manage_food():
    if not current_user.is_admin:
        flash('Access Denied.', 'danger')
        return redirect(url_for('menu'))

    items = FoodItem.query.order_by(FoodItem.category.asc(), FoodItem.name.asc()).all()
    special_offer = SpecialOffer.query.first()
    return render_template('manage_food.html', items=items, special_offer=special_offer)


@app.route('/admin/food/add', methods=['GET', 'POST'])
@login_required
def add_food():
    if not current_user.is_admin:
        flash('Access Denied.', 'danger')
        return redirect(url_for('menu'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        category = request.form['category']
        price = float(request.form['price'])
        description = request.form.get('description', '').strip()
        image = request.form.get('image', 'samosa.jpg').strip()
        available = True if request.form.get('available') else False

        new_item = FoodItem(
            name=name,
            category=category,
            price=price,
            description=description,
            image=image,
            available=available
        )
        db.session.add(new_item)
        db.session.commit()
        flash(f'"{name}" added to menu successfully!', 'success')
        return redirect(url_for('manage_food'))

    return render_template('add_food.html')


@app.route('/admin/food/edit/<int:food_id>', methods=['GET', 'POST'])
@login_required
def edit_food(food_id):
    if not current_user.is_admin:
        flash('Access Denied.', 'danger')
        return redirect(url_for('menu'))

    item = db.get_or_404(FoodItem, food_id)
    if request.method == 'POST':
        item.name = request.form['name'].strip()
        item.category = request.form['category']
        item.price = float(request.form['price'])
        item.description = request.form.get('description', '').strip()
        item.image = request.form.get('image', item.image).strip()
        item.available = True if request.form.get('available') else False

        db.session.commit()
        flash(f'"{item.name}" updated successfully!', 'success')
        return redirect(url_for('manage_food'))

    return render_template('edit_food.html', item=item)


@app.route('/admin/food/toggle/<int:food_id>')
@login_required
def toggle_food_stock(food_id):
    if not current_user.is_admin:
        flash('Access Denied.', 'danger')
        return redirect(url_for('menu'))

    item = db.get_or_404(FoodItem, food_id)
    item.available = not item.available
    db.session.commit()

    status_str = "Available" if item.available else "OUT OF STOCK"
    flash(f'"{item.name}" marked as {status_str}.', 'info')
    return redirect(url_for('manage_food'))


@app.route('/admin/food/delete/<int:food_id>')
@login_required
def delete_food(food_id):
    if not current_user.is_admin:
        flash('Access Denied.', 'danger')
        return redirect(url_for('menu'))

    item = db.get_or_404(FoodItem, food_id)
    db.session.delete(item)
    db.session.commit()
    flash(f'"{item.name}" deleted from menu.', 'warning')
    return redirect(url_for('manage_food'))


@app.route('/admin/special', methods=['GET', 'POST'])
@login_required
def edit_special():
    if not current_user.is_admin:
        flash('Access Denied.', 'danger')
        return redirect(url_for('menu'))

    offer = SpecialOffer.query.first()
    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()
        price = float(request.form['price'])
        active = True if request.form.get('active') else False

        if not offer:
            offer = SpecialOffer(title=title, description=description, price=price, active=active)
            db.session.add(offer)
        else:
            offer.title = title
            offer.description = description
            offer.price = price
            offer.active = active

        db.session.commit()
        flash("Today's Special offer updated successfully!", 'success')
        return redirect(url_for('manage_food'))

    return render_template('edit_special.html', special_offer=offer)


# ====================================================================
# STEP 12: Database Initialization & Seeding (Indian Menu)
# ====================================================================
def init_database():
    with app.app_context():
        db.create_all()

        # 1. Seed Canteen Admin
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                password=generate_password_hash('admin123'),
                full_name='Canteen Manager',
                phone='9876543210',
                is_admin=True
            )
            db.session.add(admin_user)

        # 2. Seed Demo Student
        if not User.query.filter_by(username='student').first():
            demo_student = User(
                username='student',
                password=generate_password_hash('student123'),
                full_name='Aarav Patel (22CS104)',
                phone='9123456789',
                is_admin=False
            )
            db.session.add(demo_student)

        # 3. Seed Today's Special Combo
        if not SpecialOffer.query.first():
            special = SpecialOffer(
                title='Combo: Samosa + Masala Tea',
                description='Hot crispy potato samosa served with piping hot special masala chai',
                price=25.0,
                active=True
            )
            db.session.add(special)

        # 4. Seed Realistic Indian College Canteen Food Items
        # Re-seed if empty or old basic items exist
        if FoodItem.query.count() < 10:
            FoodItem.query.delete()  # clear old 4 dummy items

            indian_menu = [
                # 🍛 Meals & Main Food
                FoodItem(name='Veg Meals', category='Meals', price=80.0, image='veg_meals.jpg',
                         description='Traditional full thali with rice, sambar, rasam, kootu, poriyal, curd & papad', order_count=42),
                FoodItem(name='Mini Meals', category='Meals', price=60.0, image='mini_meals.jpg',
                         description='Variety rice platter with lemon rice, curd rice & potato fry', order_count=28),
                FoodItem(name='Veg Fried Rice', category='Meals', price=70.0, image='veg_fried_rice.jpg',
                         description='Wok-tossed aromatic rice with fresh bell peppers, beans and carrots', order_count=55),
                FoodItem(name='Chicken Fried Rice', category='Meals', price=100.0, image='chicken_fried_rice.jpg',
                         description='Spicy canteen special wok fried rice with tender chicken chunks', order_count=64),
                FoodItem(name='Veg Noodles', category='Meals', price=70.0, image='veg_noodles.jpg',
                         description='Indo-Chinese street style Hakka noodles with soy and crunchy veggies', order_count=37),
                FoodItem(name='Chicken Noodles', category='Meals', price=100.0, image='chicken_noodles.jpg',
                         description='Hot Schezwan tossed noodles with shredded spiced chicken', order_count=49),
                FoodItem(name='Paneer Rice', category='Meals', price=90.0, image='paneer_rice.jpg',
                         description='Fragrant rice topped with rich, creamy paneer butter masala', order_count=31),

                # 🥪 Snacks & Fast Food
                FoodItem(name='Samosa', category='Snacks', price=15.0, image='samosa.jpg',
                         description='Golden triangular crispy pastry packed with spiced potato and green peas', order_count=92),
                FoodItem(name='Bajji', category='Snacks', price=15.0, image='bajji.jpg',
                         description='Batter-fried hot mirchi and potato fritters with coconut chutney', order_count=40),
                FoodItem(name='Vada', category='Snacks', price=15.0, image='vada.jpg',
                         description='Fluffy crispy medu vada served with hot sambar and chutney', order_count=36),
                FoodItem(name='Veg Puff', category='Snacks', price=25.0, image='veg_puff.jpg',
                         description='Flaky bakery pastry stuffed with spiced mixed vegetable masala', order_count=58),
                FoodItem(name='Egg Puff', category='Snacks', price=30.0, image='egg_puff.jpg',
                         description='Crispy golden puff pastry with a spiced hard-boiled egg half', order_count=67),
                FoodItem(name='Sandwich', category='Snacks', price=40.0, image='sandwich.jpg',
                         description='Toasted double-decker sandwich with cucumber, tomato, potato and mint chutney', order_count=33),
                FoodItem(name='Veg Burger', category='Fast Food', price=60.0, image='burger.jpg',
                         description='Crispy spiced vegetable patty topped with lettuce, onion and creamy mayo', order_count=48),
                FoodItem(name='French Fries', category='Fast Food', price=50.0, image='french_fries.jpg',
                         description='Crisp salted potato fingers tossed with spicy peri-peri seasoning', order_count=39),
                FoodItem(name='Pizza', category='Fast Food', price=80.0, image='pizza.jpg',
                         description='Cheesy 6-inch pan pizza topped with sweet corn, onions and capsicum', order_count=45),

                # 🍰 Desserts
                FoodItem(name='Gulab Jamun', category='Desserts', price=25.0, image='gulab_jamun.jpg',
                         description='Two warm, melt-in-the-mouth milk dumplings soaked in cardamom rose syrup', order_count=52),
                FoodItem(name='Ice Cream', category='Desserts', price=30.0, image='icecream.jpg',
                         description='Chilled double scoop ice cream cup with chocolate syrup drizzle', order_count=41),
                FoodItem(name='Brownie', category='Desserts', price=50.0, image='brownie.jpg',
                         description='Dense, fudgy dark chocolate walnut brownie square', order_count=29),
                FoodItem(name='Cake Slice', category='Desserts', price=45.0, image='cake_slice.jpg',
                         description='Soft layered Dutch truffle chocolate cake slice', order_count=21),
                FoodItem(name='Fruit Salad', category='Desserts', price=40.0, image='fruit_salad.jpg',
                         description='Bowl of diced seasonal fruits (apple, papaya, banana, pomegranate)', order_count=18),

                # 🥤 Cool Drinks & Beverages
                FoodItem(name='Tea', category='Beverages', price=10.0, image='tea.jpg',
                         description='Strong steaming hot campus special masala ginger chai', order_count=88),
                FoodItem(name='Coffee', category='Beverages', price=20.0, image='coffee.jpg',
                         description='Traditional aromatic South Indian filter coffee with frothy milk', order_count=73),
                FoodItem(name='Cold Coffee', category='Beverages', price=50.0, image='coldcoffee.jpg',
                         description='Thick chilled blended coffee topped with chocolate syrup and froth', order_count=85),
                FoodItem(name='Fresh Lime Juice', category='Beverages', price=30.0, image='fresh_lime.jpg',
                         description='Rejuvenating sweet & salt fresh lemon cooler with ice cubes', order_count=44),
                FoodItem(name='Rose Milk', category='Beverages', price=40.0, image='rose_milk.jpg',
                         description='Chilled refreshing sweet milk infused with authentic rose essence', order_count=38),
                FoodItem(name='Milkshake', category='Beverages', price=60.0, image='milkshake.jpg',
                         description='Rich blended Belgian chocolate thick shake in a tall cup', order_count=46),
                FoodItem(name='Bottled Water', category='Beverages', price=20.0, image='bottled_water.jpg',
                         description='1 Litre sealed packaged pure mineral drinking water bottle', order_count=60),
            ]
            db.session.add_all(indian_menu)

        db.session.commit()


# ====================================================================
# STEP 13: Application Runner
# ====================================================================
if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='127.0.0.1', port=5000)
