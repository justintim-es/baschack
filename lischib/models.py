from lischib import db, login_manager
from flask_login import UserMixin
from marshmallow import Schema, fields
from datetime import datetime, timedelta


@login_manager.user_loader
def load_user(organizer_id):
     return Organizer.query.get(int(organizer_id))


class Organizer(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    onboard_recognition = db.Column(db.String(256), nullable=True)
    is_onboarded = db.Column(db.Boolean, default=False)
    stripe = db.Column(db.String(120), nullable=True)
    is_confirmed = db.Column(db.Boolean, default=False)
    parties = db.relationship('Party')


class Party(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    share_stats = db.Column(db.Boolean, nullable=False)
    name = db.Column(db.String(120), unique=True, nullable=False)
    venue = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    capacity = db.Column(db.Integer, default=0)
    address_one = db.Column(db.String(120), nullable=False)
    address_two = db.Column(db.String(120), nullable=False)
    date_start = db.Column(db.DateTime(), nullable=False)
    time_start = db.Column(db.Time(), nullable=False)
    date_end = db.Column(db.DateTime(), nullable=False)
    time_end = db.Column(db.Time(), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey(
        'organizer.id'), nullable=False)
    tickettypes = db.relationship('Tickettype')
    tickets = db.relationship('Ticket')
    questions = db.relationship('CustomQuestion')
    date_created = db.Column(db.DateTime(), default=datetime.now())
    reserved = db.Column(db.Integer, default=0)
    sold = db.Column(db.Integer, default=0)


class PartySchema(Schema):
    share_stats = fields.Bool()
    name = fields.Str()
    venue = fields.Str()
    city = fields.Str()
    address_one = fields.Str()
    address_two = fields.Str()
    date_start = fields.Date()
    time_start = fields.Time()
    date_end = fields.Date()
    time_end = fields.Time()


class PartySchemaWithCapacity(PartySchema):
    capacity = fields.Int()


class CartTickettype(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tickettype_id = db.Column(db.Integer, db.ForeignKey(
        'tickettype.id'), nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    is_payed = db.Column(db.Boolean, default=False)
    quantity = db.Column(db.Integer, default=1)
    is_created = db.Column(db.Boolean, default=False)
    is_resale = db.Column(db.Boolean, default=False)
    expires = db.Column(db.DateTime(), nullable=True)
    date = db.Column(db.DateTime(), default=datetime.now())
    reserved_until = db.Column(
        db.DateTime(), nullable=False)


class CartItem:
    def __init__(self, ticket_name, quantity, price):
        self.ticket_name = ticket_name
        self.quantity = quantity
        self.price = price
        self.total_price = price * quantity
        self.is_payed = False


class CartItemSchema(Schema):
    ticket_name = fields.Str()
    quantity = fields.Int()
    price = fields.Int()
    total_price = fields.Int()
    is_payed = fields.Bool()


class Tickettype(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Integer, default=0)
    name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    sold = db.Column(db.Integer, default=0)
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'), nullable=False)
    expire = db.Column(db.DateTime(), nullable=True)
    cart_tickets = db.relationship('CartTickettype')
    left = db.column_property(quantity - sold)
    reserved = db.Column(db.Integer, default=0)
    resales = db.relationship('Resale', backref='tickettype', uselist=False)
    tickets = db.relationship('Ticket')


class TickettypeSchema(Schema):
    id = fields.Int()
    price = fields.Int()
    name = fields.Str()
    expire = fields.Date()


class TickettypeSchemaWithStats(TickettypeSchema):
    quantity = fields.Int()
    sold = fields.Int()
    left = fields.Int()


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recognition = db.Column(db.String(240))
    cart_tickets = db.relationship('CartTickettype')
    email = db.Column(db.String(120), nullable=True)
    session = db.Column(db.String(240), nullable=True)
    form = db.Column(db.String(120), nullable=True)
    tickets = db.relationship('Ticket')
    stripe = db.Column(db.String, nullable=True)
    resales = db.relationship('Resale')


class CartSchema(Schema):
    email = fields.Str()
    form = fields.Str()


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(512))
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'), nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    ticket_name = db.Column(db.String(120), nullable=False)
    resale = db.relationship('Resale', backref='ticket', uselist=False)
    is_resold = db.Column(db.Boolean, default=False)
    tickettype_id = db.Column(db.Integer, db.ForeignKey('tickettype.id'), nullable=False)


class Resale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Integer, default=0)
    is_resold = db.Column(db.Boolean, default=False)
    link = db.Column(db.String, nullable=True)
    session = db.Column(db.String, nullable=True)
    reserved = db.Column(db.Boolean, default=False)
    date_reserved = db.Column(db.DateTime, nullable=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey(
        'ticket.id'), nullable=False, unique=True)
    tickettype_id = db.Column(db.Integer, db.ForeignKey('tickettype.id'), nullable=False)
    cart_tickettype_id = db.Column(db.Integer, db.ForeignKey('cart_tickettype.id'), nullable=False)


class ResaleSchema(Schema):
    id = fields.Int()
    price = fields.Int()
    is_resold = fields.Bool()
    link = fields.Str()
    session = fields.Str()
    reserved = fields.Bool()
    date_reserved = fields.Date()


class TicketSchema(Schema):
    id = fields.Int()
    party_id = fields.Int()
    cart_id = fields.Int()
    ticket_name = fields.Str()
    resale = fields.Nested(ResaleSchema())


class TicketValueSchema(TicketSchema):
    value = fields.Str()


class TicketResale:
    def __init__(self, resale_id, price, is_resold, link, reserved, date_reserved, ticket_name):
        self.resale_id = resale_id
        self.price = price
        self.is_resold = is_resold
        self.link = link
        self.reserved = reserved
        self.date_reserved = date_reserved
        self.ticket_name = ticket_name


class TicketResaleSchema(Schema):
    resale_id = fields.Int()
    price = fields.Int()
    is_resold = fields.Bool()
    link = fields.Str()
    session = fields.Str()
    reserved = fields.Str()
    date_reserved = fields.Date()
    ticket_name = fields.Str()


class CustomQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'), nullable=False)
    question = db.Column(db.String)


class CustomQuestionSchema(Schema):
    question = fields.Str()


class CustomAnwerSchema(Schema):
    question = fields.Str()
    answer = fields.Str()


class CartVisitor:
    def __init__(self, email, form, cart_tickets):
        self.email = email
        self.form = form
        self.cart_tickets = cart_tickets
