from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_login import LoginManager
from flask_cors import CORS
app = Flask(__name__)
cors = CORS(app, resources={r"*": {"origins": "*"}})
app.config['SECRET_KEY'] = 'f935feed8409ec387475f571586a2682dcd677336ec9678020fc1f533ff2214c'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://doadmin:AVNS_WqlbQNhW6kkIyWdykb6@db-postgresql-ams3-55936-do-user-7460943-0.b.db.ondigitalocean.com:25060/tickettype'
login_manager = LoginManager(app)
app.config['MAIL_SERVER'] = 'smtp.hostnet.nl'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'confirm@ticketty.pe'
app.config['MAIL_PASSWORD'] = 'Coschon32!'
app.config['MAIL_USERNAME'] = 'tickets@ticketty.pe'
app.config['MAIL_PASSWORD'] = 'Tischick32!'
db = SQLAlchemy(app)

mail = Mail(app)
import lischib.routs
