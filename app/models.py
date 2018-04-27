from datetime import datetime
from werkzeug.security import (generate_password_hash, check_password_hash)

from app import db
from app import login

from flask_login import UserMixin


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ACTIVITIES = 0x04
    MODERATE_ACTIVITIES = 0x08
    ADMINISTER = 0x80


def initial_values():
    Role.insert_initial()
    Account_type.insert_initial()
    Account_contact_type.insert_initial()
    Account_address_type.insert_initial()
    Account_activity_type.insert_initial()
    Account_data_type.insert_initial()
    Account_credit.insert_initial()

    House_status.insert_initial()


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(54), unique=True)
    default = db.Column(db.Boolean, index=True)
    permissions = db.Column(db.Integer)

    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_initial():
        roles = {
            'Ventas': (
                Permission.FOLLOW |
                Permission.COMMENT |
                Permission.WRITE_ACTIVITIES, True),
            'Moderador': (
                Permission.FOLLOW |
                Permission.COMMENT |
                Permission.WRITE_ACTIVITIES |
                Permission.MODERATE_ACTIVITIES, False),
            'Administrador': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    phone = db.Column(db.String(30))
    username = db.Column(db.String(54), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username

    def can(self, permissions):
        return (
            self.role is not None and
            (self.role.permissions & permissions) == permissions)

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    # -----------------------
    # Relationships for accounts
    accounts = db.relationship('Account', backref='user', lazy='dynamic')

    accounts_comments = db.relationship(
            'Account_comment', backref='user', lazy='dynamic')

    accounts_activities_created = db.relationship(
            'Account_activity',
            backref='creator',
            primaryjoin="Account_activity.creator_id==User.id",
            lazy='dynamic')

    accounts_activities_assigned = db.relationship(
            'Account_activity',
            backref='responsable',
            primaryjoin="Account_activity.assigned_to_id==User.id",
            lazy='dynamic')

    accounts_activities_comments = db.relationship(
            'Account_activity_comment',
            backref='user',
            lazy='dynamic')

    sold_houses = db.relationship(
            'House',
            backref='user',
            primaryjoin="House.seller_id==User.id",
            lazy='dynamic')


# Account classes
class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    email = db.Column(db.String(64))
    phone = db.Column(db.String(30))
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    account_type_id = db.Column(
            db.Integer,
            db.ForeignKey('account_type.id'))
    account_contact_type_id = db.Column(
            db.Integer,
            db.ForeignKey('account_contact_type.id'))

    account_credit_id = db.Column(
            db.Integer,
            db.ForeignKey('account_credit.id'))

    creator_id = db.Column(
            db.Integer,
            db.ForeignKey('users.id'))

    addresses = db.relationship(
            'Account_address', backref='account',
            lazy='dynamic', cascade="all, delete-orphan")
    activities = db.relationship(
            'Account_activity', backref='account',
            lazy='dynamic', cascade="all, delete-orphan")
    comments = db.relationship(
            'Account_comment', backref='account',
            lazy='dynamic', cascade="all, delete-orphan")
    data = db.relationship(
            'Account_data', backref='account',
            lazy='dynamic', cascade="all, delete-orphan")
    houses = db.relationship(
            'House', backref='account', lazy='dynamic')

    def __repr__(self):
        return '<Account %r>' % self.name


class Account_type(db.Model):
    __tablename__ = 'account_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

    accounts = db.relationship('Account', backref='type', lazy='dynamic')

    def __repr__(self):
        return '<Account type %r>' % self.name

    @staticmethod
    def insert_initial():
        types = ['Cliente', 'Contacto', 'Inquilino', 'Descartado']

        for type in types:
            new_type = Account_type.query.filter_by(name=type).first()

            if new_type is None:
                new_type = Account_type(name=type)

            db.session.add(new_type)

        db.session.commit()


class Account_contact_type(db.Model):
    __tablename__ = 'account_contact_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

    accounts = db.relationship(
            'Account', backref='contact_type', lazy='dynamic')

    def __repr__(self):
        return '<Account type %r>' % self.name

    @staticmethod
    def insert_initial():
        types = [
            'Vivanuncio', 'Vendedor', 'Amigo',
            'Folleto', 'Lona', 'Segunda mano', 'Pagina web']

        for type in types:
            new_type = Account_contact_type.query.filter_by(name=type).first()

            if new_type is None:
                new_type = Account_contact_type(name=type)

            db.session.add(new_type)

        db.session.commit()


class Account_address(db.Model):
    __tablename__ = 'account_address'
    id = db.Column(db.Integer, primary_key=True)
    street = db.Column(db.String(64))
    city = db.Column(db.String(64))
    state = db.Column(db.String(64))
    code = db.Column(db.String(20))
    country = db.Column(db.String(30))
    phone = db.Column(db.String(30))
    description = db.Column(db.String(64))
    type_id = db.Column(
            db.Integer, db.ForeignKey('account_address_type.id'))

    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))

    def __repr__(self):
        return (
                '<Account address %r: %r - %r>' %
                (self.description, self.street, self.city))


class Account_address_type(db.Model):
    __tablename__ = 'account_address_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))

    addresses = db.relationship(
            'Account_address', backref='type', lazy='dynamic')

    def __repr__(self):
        return '<Account address type %r>' % (self.name)

    @staticmethod
    def insert_initial():
        types = ['Casa', 'Oficina', 'Trabajo', 'Familiar']

        for type in types:
            new_type = Account_address_type.query.filter_by(name=type).first()

            if new_type is None:
                new_type = Account_address_type(name=type)

            db.session.add(new_type)

        db.session.commit()


class Account_activity(db.Model):
    __tablename__ = 'account_activity'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60))
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    completed = db.Column(db.Boolean)

    type_id = db.Column(db.Integer, db.ForeignKey('account_activity_type.id'))
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    comments = db.relationship(
            'Account_activity_comment', backref='activity',
            lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return '<Account activity %r>' % (self.timestamp)


class Account_activity_type(db.Model):
    __tablename__ = 'account_activity_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))

    activities = db.relationship(
            'Account_activity', backref='type', lazy='dynamic')

    def __repr__(self):
        return '<Account activity type %r>' % (self.name)

    @staticmethod
    def insert_initial():
        types = ['Correo', 'Llamada', 'Visita', 'Entrega', 'Seguimiento']

        for type in types:
            new_type = Account_activity_type.query.filter_by(name=type).first()

            if new_type is None:
                new_type = Account_activity_type(name=type)

            db.session.add(new_type)

        db.session.commit()


class Account_activity_comment(db.Model):
    __tablename__ = 'account_activity_comment'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    activity_id = db.Column(db.Integer, db.ForeignKey('account_activity.id'))
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<Account activity comment %r>' % (self.timestamp)


class Account_comment(db.Model):
    __tablename__ = 'account_comment'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<Account comment %r>' % (self.timestamp)


class Account_data(db.Model):
    __tablename__ = 'account_data'
    id = db.Column(db.Integer, primary_key=True)
    info = db.Column(db.String(100))

    type_id = db.Column(db.Integer, db.ForeignKey('account_data_type.id'))
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))

    def __repr__(self):
        return '<Account data %r>' % (self.info)


class Account_data_type(db.Model):
    __tablename__ = 'account_data_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))

    data = db.relationship(
            'Account_data', backref='type', lazy='dynamic')

    def __repr__(self):
        return '<Account data type %r>' % (self.name)

    @staticmethod
    def insert_initial():
        types = ['NSS', 'RFC', 'Fecha de nacimiento',
                 'Conyuge', 'Telefono extra', 'CURP']

        for type in types:
            new_type = Account_data_type.query.filter_by(name=type).first()

            if new_type is None:
                new_type = Account_data_type(name=type)

            db.session.add(new_type)

        db.session.commit()


class Account_credit(db.Model):
    __tablename__ = 'account_credit'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))

    accounts = db.relationship(
            'Account', backref='credit', lazy='dynamic')

    def __repr__(self):
        return '<Account credit type %r>' % (self.name)

    @staticmethod
    def insert_initial():
        types = ['Infonavit', 'Fovissste', 'Bancario',
            'Contado', 'Cancelado', 'Desconocido']

        for type in types:
            new_type = Account_credit.query.filter_by(name=type).first()

            if new_type is None:
                new_type = Account_credit(name=type)

            db.session.add(new_type)

        db.session.commit()


# House classes
class House(db.Model):
    __tablename__ = 'houses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    address = db.Column(db.String(64))
    cuv = db.Column(db.String(20))
    price = db.Column(db.Float())

    complex_id = db.Column(db.Integer, db.ForeignKey('houses_complex.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('houses_status.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<House %r>' % self.name


class House_status(db.Model):
    __tablename__ = 'houses_status'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

    houses = db.relationship('House', backref='status', lazy='dynamic')

    def __repr__(self):
        return '<Status %r>' % self.name

    @staticmethod
    def insert_initial():
        types = [
            'Vendida', 'Apartada', 'Construccion',
            'Lote', 'Entregada', 'En venta']

        for type in types:
            new_type = House_status.query.filter_by(name=type).first()

            if new_type is None:
                new_type = House_status(name=type)

            db.session.add(new_type)

        db.session.commit()


# House Complex classes
class House_complex(db.Model):
    __tablename__ = 'houses_complex'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    address = db.Column(db.String(100))
    city = db.Column(db.String(64))
    state = db.Column(db.String(64))
    country = db.Column(db.String(64))
    zipcode = db.Column(db.String(64))

    houses = db.relationship(
            'House', backref='complex',
            lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return '<House %r>' % self.name
