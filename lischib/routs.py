from flask import render_template, redirect, url_for, make_response, jsonify, request
from lischib import app, db, mail
from lischib.forms import OrganizerRegisterForm, OrganizerLoginForm, CreateEventForm, CreateTickettypeForm, CustomQuestionForm, OnboardForm
from lischib.models import Organizer, Party, Ticket, PartySchema, PartySchemaWithCapacity, CartTickettype, TickettypeSchema, TickettypeSchemaWithStats, Cart, CartItem, CartItemSchema, Tickettype, CustomQuestion, CustomQuestionSchema, TicketSchema, CartSchema, Resale, ResaleSchema, TicketValueSchema, TicketResale, TicketResaleSchema, CartVisitor
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer as urls
from flask_mail import Message
from flask_login import login_user, login_required, current_user
from secrets import token_hex
from datetime import datetime, timedelta
import stripe
bcrypt = Bcrypt(app)
stripe.api_key = 'sk_test_51KVxlPAGQn2FqgzDtqLjvtGTOEEFqOVjNCMALmXVSodlaplQ6hHE1yczSONPOSGa8GVRpVUyGhnKQ3zYEfVvaeWM001Wtrx9YB'


@app.route('/register', methods=["GET", "POST"])
def register():
    form = OrganizerRegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode('utf-8')
        organizer = Organizer(email=form.email.data, password=hashed_password)
        db.session.add(organizer)
        db.session.commit()
        s = urls(app.config['SECRET_KEY'])
        token = s.dumps({'organizer_id': organizer.id})
        msg = Message('Confirm e-mail request',
                      sender="confirm@ticketty.pe", recipients=[organizer.email])
        msg.body = f'''
            Could you confirm your e-mail, please press on the link below:
            https://admin.openticket.sale{url_for('confirm', token=token)}
        '''
        mail.send(msg)
        return redirect(url_for('please'))
    return render_template('register.html', form=form)


@app.route('/please')
def please():
    return render_template('please.html')


@app.route("/login", methods=["GET", "POST"])
def login():
    print('haschalloscho')
    form = OrganizerLoginForm()
    if form.validate_on_submit():
        print('wasvalid')
        organizer = Organizer.query.filter_by(email=form.email.data).first()
        if organizer and bcrypt.check_password_hash(organizer.password, form.password.data):
            print('gothere')
            login_user(organizer)
            return redirect(url_for('dashboard'))
    return render_template("login.html", form=form)


@app.route('/confirm/<token>', methods=["POST", "GET"])
def confirm(token):
    s = urls(app.config['SECRET_KEY'])
    payload = s.loads(token)
    recognition = token_hex(64)
    organizer = Organizer.query.filter_by(id=payload['organizer_id']).first()
    organizer.is_confirmed = True
    organizer.onboard_recognition = recognition
    form = OnboardForm()
    if form.validate_on_submit():
        if form.is_nl.data:
            aschac = stripe.Account.create(
                type="express",
                email=organizer.email,
                country="nl",
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
            )
            organizer.stripe = aschac.id   
            link = stripe.AccountLink.create(
                    account=aschac.id,
                    refresh_url='https://admin.ticketty.pe/confirm/' + token,
                    return_url='https://admin.ticketty.pe/onboarded/' + recognition,
                    type="account_onboarding"
            )
            db.session.commit()
            return redirect(link.url)
        else:
            aschac = stripe.Account.create(
            type="express",
                 email=organizer.email,
                capabilities={
                        "card_payments": {"requested": True},
                        "transfers": {"requested": True},
                 },
            )
            organizer.stripe = aschac.id
            link = stripe.AccountLink.create(
                    account=aschac.id,
                    refresh_url='https://admin.ticketty.pe/confirm/' + token,
                    return_url='https://admin.ticketty.pe/onboarded/' + recognition,
                    type="account_onboarding"
            )
            db.session.commit()
            return redirect(link.url)
    return render_template('confirm.html', form=form)

@app.route('/onboarded/<recognition>', methods=["GET", "POST"])
def onboarded(recognition):
    organizer = Organizer.query.filter_by(
        onboard_recognition=recognition).first()
    organizer.is_onboarded = True
    db.session.commit()
    return redirect(url_for('login'))


@app.route('/dashboard', methods=["GET"])
def dashboard():
    parties = Party.query.filter_by(organizer_id=current_user.id).all()
    parties.sort(key=lambda p: p.date_created)
    parties.reverse()
    return render_template('dashboard.html', parties=parties)


@app.route('/create-event', methods=["GET", "POST"])
@login_required
def create_event():
    form = CreateEventForm()
    if form.validate_on_submit():
        party = Party(
            share_stats=form.share_stats.data,
            name=form.name.data,
            venue=form.venue.data,
            city=form.city.data,
            capacity=form.capacity.data,
            address_one=form.address_one.data,
            address_two=form.address_two.data,
            date_start=form.date_start.data,
            time_start=form.time_start.data,
            date_end=form.date_end.data,
            time_end=form.time_end.data,
            organizer_id=current_user.id
        )
        db.session.add(party)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('create_event.html', form=form)


@app.route('/event/<event_id>')
@login_required
def event(event_id):
    event = Party.query.filter_by(id=event_id).first()
    tickets = Tickettype.query.filter_by(party_id=event_id).all()
    sold = 0
    reserved = 0
    for t in tickets:
        sold += t.sold
        reserved += t.reserved
    orders = []
    for t in tickets:
        cts = CartTickettype.query.filter_by(
            tickettype_id=t.id, is_payed=True, is_created=True).all()
        for ct in cts:
            cart = Cart.query.get(ct.cart_id)
            your_cts = CartTickettype.query.filter_by(cart_id=cart.id).all()
            for y_cts in your_cts:
                resales = Resale.query.filter_by(cart_tickettype_id=y_cts.id).all()
                y_cts.resales = resales
                y_cts.ticket_name = Tickettype.query.get(
                    y_cts.tickettype_id).name
            orders.append(CartVisitor(cart.email, cart.form, your_cts))
                

    return render_template('event.html', party=event, sold=sold, tickets=tickets, reserved=reserved, orders=orders)



@app.route('/event/resale/<event_id>/<id>')
@login_required
def event_resale(event_id, id):
    resale = Resale.query.get(int(id))
    cart = Cart.query.get(resale.cart_id)
    cart_tickettype = CartTickettype.query.filter_by(cart_id=cart.id, is_resale=True).first()
    resale_again = Resale.query.filter_by(cart_tickettype_id=cart_tickettype.id).first()
    if resale_again:
        return render_template('resale.html', resale=resale, cart=cart,  event_id=event_id, resale_again=resale_again)
    else:
     return render_template('resale.html', resale=resale, cart=cart, event_id=event_id)
    
@app.route('/create-tickettype/<event_id>', methods=["GET", "POST"])
@login_required
def create_tickettype(event_id):
    form = CreateTickettypeForm()
    form.event_id = event_id
    if form.validate_on_submit():
        tickettype = Tickettype(
            price=form.price.data,
            name=form.name.data,
            quantity=form.quantity.data,
            party_id=event_id,
            expire=form.expire.data,
        )
        db.session.add(tickettype)
        db.session.commit()
        return redirect(url_for('event', event_id=event_id))
    return render_template('create_tickettype.html', form=form)


@app.route('/create-custom-question/<event_id>', methods=["GET", "POST"])
@login_required
def create_custom_question(event_id):
    form = CustomQuestionForm()
    if form.validate_on_submit():
        custom_question = CustomQuestion(
            question=form.question.data, party_id=event_id)
        db.session.add(custom_question)
        db.session.commit()
        return redirect(url_for('event', event_id=event_id))
    questions = CustomQuestion.query.filter_by(party_id=event_id).all()
    return render_template("custom.html", form=form, questions=questions)


@app.route('/adjust-event/<event_id>', methods=["GET", "POST"])
@login_required
def adjust_event(event_id):
    event = Party.query.get(int(event_id))
    form = CreateEventForm(obj=event)
    if form.validate_on_submit():
        event.share_stats = form.share_stats.data
        event.name = form.name.dat
        event.venue = form.venue.data
        event.city = form.city.data
        event.capacity = form.capacity.data
        event.address_one = form.address_one.data
        event.address_two = form.address_two.data
        event.date_start = form.date_start.data
        event.time_start = form.time_start.data
        event.date_end = form.date_end.data
        event.time_end = form.time_end.data
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('create_event.html', party=event, form=form)


@app.route('/adjust-tickettype/<event_id>/<tickettype_id>', methods=["GET", "POST"])
@login_required
def adjust_tickettype(event_id, tickettype_id):

    tickettype = Ticket.query.get(int(tickettype_id))
    form = CreateTickettypeForm(obj=tickettype)
    form.event_id = event_id
    if form.validate_on_submit():
        tickettype.price = form.price.data
        tickettype.name = form.name.data
        tickettype.quantity = form.quantity.data
        tickettype.expire = form.expire.data
        db.session.commit()
        return redirect(url_for('event', event_id=event_id))
    return render_template('create_tickettype.html', form=form)


@app.route('/api/event/<event_id>', methods=["GET"])
def api_event(event_id):
    party = Party.query.get(int(event_id))
    sold = 0
    tickettypes = Tickettype.query.filter_by(party_id=event_id).all()
    for t in Ticket.query.filter_by(party_id=party.id).all():
        for ct in CartTickettype.query.filter_by(tickettype_id=t.id, is_payed=True).all():
            sold += ct.quantity
    for tickettype in tickettypes:
        for c_t in CartTickettype.query.filter_by(tickettype_id=tickettype.id).all():
            if datetime.now() > c_t.reserved_until:
                while tickettype.reserved > 0:
                    if tickettype.reserved == 0: break
                    tickettype.reserved -= c_t.quantity
    db.session.commit()
    if party.share_stats:
        pSchema = PartySchemaWithCapacity()
        tSchema = TickettypeSchemaWithStats()
        return make_response({'party': pSchema.dump(party),  'sold': sold, 'tickettypes': tSchema.dump(tickettypes, many=True)}, 200)
    else:
        pSchema = PartySchema()
        tSchema = TickettypeSchema()
        return make_response({'party': pSchema.dump(party), 'tickettypes': tSchema.dump(tickettypes, many=True)}, 200)


@app.route('/api/create-cart', methods=["POST"])
def api_create_cart():
    json = request.json
    recognition = token_hex(64)
    cart = Cart(recognition=recognition)
    db.session.add(cart)
    db.session.commit()
    ticket_id = json['ticket_id']
    quantity = json['quantity']
    tickettype = Tickettype.query.get(int(ticket_id))
    if (tickettype.quantity - tickettype.sold - tickettype.reserved) < quantity:
        return make_response("Not enough tickets left", 400)
    tickettype.reserved += quantity

    cart_ticket = CartTickettype(
        tickettype_id=ticket_id,
        cart_id=cart.id,
        quantity=quantity,
        is_payed=False,
    )
    db.session.add(cart_ticket)

    db.session.commit()
    print(tickettype.reserved)
    return make_response({
        'recognition': recognition,
    }, 200)


@app.route('/api/adjust-cart/<recognition>', methods=["POST"])
def api_adjust_cart(recognition):
    json = request.json
    cart = Cart.query.filter_by(recognition=recognition).first()
    quantity = json['quantity']
    cart_ticket = CartTickettype.query.filter_by(
        tickettype_id=json['ticket_id'],
        cart_id=cart.id).first()
    if cart_ticket:
        tickettype = Tickettype.query.get(int(json['ticket_id']))
        tickettype.reserved -= cart_ticket.quantity
        if (tickettype.quantity - tickettype.sold - tickettype.reserved) < quantity:
            return make_response("Not enough tickets left", 400)
        tickettype.reserved += quantity
        cart_ticket.quantity = quantity
    else:
        tickettype = Tickettype.query.get(int(json['ticket_id']))
        if (tickettype.quantity - tickettype.sold - tickettype.reserved) < quantity:
            return make_response("Not enough tickets left", 400)
        new_cart_ticket = CartTickettype(
            tickettype_id=json['ticket_id'],
            cart_id=cart.id,
            quantity=json['quantity'],
            is_payed=False
         )
        db.session.add(new_cart_ticket)
    db.session.commit()
    return make_response("", 200)


@app.route('/api/cart/<event>/<recognition>')
def api_cart(event, recognition):
    cart = Cart.query.filter_by(recognition=recognition).first()
    cart_tickets = CartTickettype.query.filter_by(cart_id=cart.id, is_payed=False).all()
    cart_items = []
    for ct in cart_tickets:
        ticket = Tickettype.query.get(int(ct.tickettype_id))
        cart_items.append(CartItem(ticket.name, ct.quantity, ticket.price))
        if datetime.now() > ct.reserved_until:
            return make_response("Time is up your order has expired", 400)
    total_price = 0
    for ci in cart_items:
        total_price += ci.total_price
    party = Party.query.get(int(event))
    organizer = Organizer.query.get(party.organizer_id)
    schema = CartItemSchema()
    session = stripe.checkout.Session.create(
        success_url="https://ticketty.pe/create/" + event + '/' + recognition,
        cancel_url="https://ticketty.pe/checkout/" + event + '/' + recognition,
        line_items=[
            {
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': f'Tickets for {party.name}'
                    },
                    'unit_amount': total_price
                },
                'quantity': 1
            }
        ],
        payment_method_types=['card'],
        mode="payment",
        payment_intent_data={
            'application_fee_amount': 29
        },
        stripe_account=organizer.stripe
    )
    cart.session = session.id
    db.session.commit()
    cartSchema = CartSchema()
    return make_response({
        'items': schema.dump(cart_items, many=True),
        'total_price': total_price,
        'url': session.url,
        'cart': cartSchema.dump(cart)
    }, 200)


@app.route('/api/create/<event>/<recognition>', methods=["POST"])
def create(event, recognition):
    cart = Cart.query.filter_by(recognition=recognition).first()
    party = Party.query.get(int(event))
    organizer = Organizer.query.get(party.organizer_id)
    session = stripe.checkout.Session.retrieve(
        cart.session, None, stripe_account=organizer.stripe)
    if session.payment_status != "paid":
        return make_response("Payment failed", 400)
    elif session.payment_status == "paid":
        cart_tickettypes = CartTickettype.query.filter_by(
            cart_id=cart.id).all()
        for c_t in cart_tickettypes:
            c_t.is_payed = True
            if not c_t.is_created:
                for i in range(c_t.quantity):
                    tickettype = Tickettype.query.get(c_t.tickettype_id)
                    ticket = Ticket(value=token_hex(256), party_id=event,
                                    cart_id=cart.id, ticket_name=tickettype.name, tickettype_id=tickettype.id)
                    db.session.add(ticket)
                    tickettype.sold += 1
                    tickettype.reserved -= 1
                c_t.is_created = True
        db.session.commit()
        msg = Message(f'Tickets for  {party.name}',
                      sender="tickets@ticketty.pe", recipients=[cart.email])
        msg.body = f'''
            Your tickets are in the link below:
            https://ticketty.pe/tickets/{event}/{recognition}
        '''
        mail.send(msg)
    return make_response("", 200)


@app.route('/api/questions/<event_id>')
def api_questions(event_id):
    custom_questions = CustomQuestion.query.filter_by(party_id=event_id).all()
    schema = CustomQuestionSchema()
    return make_response(schema.dump(custom_questions, many=True), 200)


@app.route('/api/form/<recognition>', methods=["POST"])
def api_form(recognition):
    json = request.json
    print(json['email'])
    print(json['customs'])
    cart = Cart.query.filter_by(recognition=recognition).first()
    cart.email = json['email']
    cart.form = str(json['customs'])
    db.session.commit()
    return make_response("", 200)


@app.route('/api/tickets/<event>/<recognition>', methods=["GET"])
def api_tickets(event, recognition):
    ticket_codes = []
    cart = Cart.query.filter_by(recognition=recognition).first()
    tickets = Ticket.query.filter_by(
        party_id=event, cart_id=cart.id).all()
    for ticket in tickets:
        print(ticket.resale)
    ticket_schema = TicketValueSchema()
    return make_response(ticket_schema.dump(tickets, many=True), 200)


@app.route('/api/tickets/onboard/<event>/<value>/<recognition>', methods=["GET"])
def api_tickets_onboard(event, value, recognition):
    cart = Cart.query.filter_by(recognition=recognition).first()
    if cart.stripe:
        return make_response("", 200)
    aschac = stripe.Account.create(
        type="express",
        email=cart.email,
        capabilities={
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
        },
    )
    cart.stripe = aschac.id
    link = stripe.AccountLink.create(
        account=aschac.id,
        refresh_url='https://ticketty.pe/tickets/' + event + '/' + recognition,
        return_url='https://ticketty.pe/tickets-sell/'
        + event + '/' + recognition + '/' + value,
        type="account_onboarding"
    )
    db.session.commit()
    return make_response({
        'link': link.url
    }, 201)


@app.route('/api/tickets/sell/<event>/<recognition>/<value>', methods=["POST"])
def api_tickets_sell(event, recognition, value):
    json = request.json
    ticket = Ticket.query.filter_by(value=value).first()
    cart = Cart.query.filter_by(recognition=recognition).first()
    cart_tickettype= CartTickettype.query.filter_by(cart_id=cart.id).first()
    price = int(json['price']) * 100
    resale = Resale(
        price=price,
        ticket_id=ticket.id,
        tickettype_id=cart_tickettype.tickettype_id,
        cart_tickettype_id=cart_tickettype.id
    )
    db.session.add(resale)
    db.session.commit()
    session = stripe.checkout.Session.create(
        success_url="https://ticketty.pe/redeem/"
        + event + '/' + str(resale.id) + '/' + recognition,
        cancel_url="https://ticketty.pe/resale/" + event,
        line_items=[
            {
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Buy second hand ticket'
                    },
                    'unit_amount': price
                },
                'quantity': 1
            }
        ],
        payment_method_types=['card'],
        mode="payment",
        payment_intent_data={
            'application_fee_amount': 24
        },
        stripe_account=cart.stripe
    )
    resale.session = session.id
    resale.link = session.url
    db.session.commit()
    return make_response("", 200)


@app.route('/api/resale/<event>')
def api_resale(event):
    tickets = Ticket.query.filter_by(party_id=event).all()
    resales = []
    for ticket in tickets:
        if ticket.resale and not ticket.is_resold:
            resales.append(ticket)
    schema = TicketSchema()
    return make_response(schema.dump(resales, many=True), 200)


@app.route('/api/resale/cancel/<id>', methods=["DELETE"])
def api_resale_cancel(id):
    resale = Resale.query.get(int(id))
    if resale.is_resold:
        return make_response("ticket is already sold", 400)
    if resale.reserved:
        return make_response("Ticket is already ordered", 400)
    db.session.delete(resale)
    db.session.commit()
    return make_response("", 200)


@app.route('/api/resale/reserve/<id>', methods=["POST"])
def api_resale_reserve(id):
    resale = Resale.query.get(id)
    if resale.reserved:
        if datetime.now() < resale.date_reserved:
            return make_response("Ticket is already reserved", 400)
    resale.reserved = True
    resale.date_reserved = datetime.now() + timedelta(minutes=20)
    new_recognition = token_hex(64)
    cart = Cart(recognition=new_recognition)
    db.session.add(cart)
    db.session.commit()
    ticket = Ticket.query.get(resale.ticket_id)

    cart_ticket = CartTickettype(
        tickettype_id=ticket.tickettype_id,
        cart_id=cart.id,
        quantity=1,
        is_payed=False,
        is_resale=True
    )
    db.session.add(cart_ticket)
    resale.cart_id = cart.id
    db.session.commit()
    return make_response(new_recognition, 200)


@app.route('/api/resale/checkout/<resale_id>/<recognition>')
def api_resale_checkout(resale_id, recognition):
    cart = Cart.query.filter_by(recognition=recognition).first()
    cschema = CartSchema()
    resale = Resale.query.get(int(resale_id))
    ticket = Ticket.query.get(int(resale.ticket_id))
    tschema = TicketSchema()
    return make_response({
        'cart': cschema.dump(cart),
        'ticket': tschema.dump(ticket)
    }, 200)


@app.route('/api/resale/redeem/<id>/<old_recognition>')
def api_resale_redeem(id, old_recognition):
    old_cart = Cart.query.filter_by(recognition=old_recognition).first()
    resale = Resale.query.get(id)
    ticket = Ticket.query.get(resale.ticket_id)
    session = stripe.checkout.Session.retrieve(
        resale.session, None, stripe_account=old_cart.stripe)
    if session.payment_status != "paid":
        return make_response("Payment failed", 200)
    elif session.payment_status == "paid":
        if ticket.is_resold:
            return make_response("Tickets already generated!", 400)
        resale.is_resold = True
        ticket.is_resold = True
        new_ticket = Ticket(
            value=token_hex(256),
            party_id=ticket.party_id,
            cart_id=resale.cart_id,
            ticket_name=ticket.ticket_name,
            tickettype_id=ticket.tickettype_id
        )
        db.session.add(new_ticket)
        db.session.commit()
        party = Party.query.get(ticket.party_id)
        new_cart = Cart.query.get(resale.cart_id)
        msg = Message(f'Tickets for  {party.name}',
                      sender="tickets@ticketty.pe", recipients=[new_cart.email])
        msg.body = f'''
            Your tickets are in the link below:
            https://ticketty.pe/tickets/{ticket.party_id}/{new_cart.recognition}
        '''
        mail.send(msg)
        return make_response({
            'recognition': new_cart.recognition
        }, 200)
