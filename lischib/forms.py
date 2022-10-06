from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email, Length, Optional
from wtforms import StringField, PasswordField, SubmitField, ValidationError, DateField, TimeField, IntegerField, BooleanField
from lischib.models import Organizer, Party, Ticket, Tickettype


class OrganizerRegisterForm(FlaskForm):
    email = StringField(
        'E-Mail', validators=[DataRequired(), Length(min=2), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self, email):
        organizer = Organizer.query.filter_by(email=email.data).first()
        if organizer:
            raise ValidationError(
                'That username is taken. Please choose a different one')


class OrganizerLoginForm(FlaskForm):
    email = StringField(
        'E-Mail', validators=[DataRequired(), Length(min=2), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class CreateEventForm(FlaskForm):
    share_stats = BooleanField('Share ticket statistics')
    name = StringField('Name', validators=[DataRequired()])
    venue = StringField('Venue', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    capacity = IntegerField('Capacity', validators=[DataRequired()])
    address_one = StringField('Address one', validators=[DataRequired()])
    address_two = StringField('Address two', validators=[DataRequired()])
    date_start = DateField('Begin date', validators=[DataRequired()])
    time_start = TimeField('Time start', validators=[DataRequired()])
    date_end = DateField('End date', validators=[DataRequired()])
    time_end = TimeField('Time end')
    submit = SubmitField('create/adjust event')


class CreateTickettypeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    price = IntegerField('Price in cents', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    expire = DateField('Expires on (optional)', validators=[Optional()])
    submit = SubmitField('create/adjust ticketty.pe')

    def validate_quantity(self, quantity):
        event_id = int(self.event_id)
        party = Party.query.get(event_id)
        tickets = Tickettype.query.filter_by(party_id=event_id).all()
        inner_quantity = quantity.data
        for t in tickets:
            inner_quantity += t.quantity
        if inner_quantity > party.capacity:
            raise ValidationError(
                f'Quantity exceeds event capacity {party.capacity}')


class CustomQuestionForm(FlaskForm):
    question = StringField('Question', validators=[DataRequired()])
    submit = SubmitField('add custom question')



class OnboardForm(FlaskForm):
    is_nl = BooleanField('Is your company based in the Netherlands')
    submit = SubmitField('onboard')
