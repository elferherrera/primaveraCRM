from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField,
                     SubmitField, SelectField, TextAreaField,
                     DateTimeField)
from wtforms.validators import (DataRequired, ValidationError, Email,
                                EqualTo, Length, Regexp)

from app.models import (User, Role, Account_type,
                        Account_contact_type, Account_address_type,
                        Account_data_type, Account_activity_type,
                        Account_credit, House_status)


class LoginForm(FlaskForm):
    email = StringField('Correo', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Mantenerme conectado')
    submit = SubmitField('Entrar')


class UserForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()])
    username = StringField('Usuario', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Telefono', validators=[DataRequired()])
    location = StringField('Ubicación', validators=[DataRequired()])

    change_pw = BooleanField('Cambiar password')
    password = PasswordField('Password')
    password2 = PasswordField(
            'Repetir password', validators=[EqualTo('password')])
    submit = SubmitField('Salvar')

    def __init__(self, user=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)

        if user is not None:
            self.user = user
        else:
            self.user = User()

    def validate_change_pw(self, field):
        if field.data is True:
            self.password.valIdators = [
                    DataRequired(),
                    EqualTo(
                        'password',
                        message='Passwords deben ser iguales.')]

    def validate_email(self, field):
        if (field.data != self.user.email
                and User.query.filter_by(email=field.data).first()):

            raise ValidationError('Correo ya en uso.')

    def validate_username(self, field):
        if (field.data != self.user.username
                and User.query.filter_by(username=field.data).first()):

            raise ValidationError('Nombre ya en uso.')


class UserAdminForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()])
    username = StringField('Usuario', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Telefono', validators=[DataRequired()])
    location = StringField('Ubicación', validators=[DataRequired()])
    role = SelectField('Tipo', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Salvar')

    def __init__(self, user, *args, **kwargs):
        super(UserAdminForm, self).__init__(*args, **kwargs)

        self.user = user
        self.role.choices = [
            (role.id, role.name) for
            role in Role.query.order_by(Role.name).all()]

    def validate_email(self, field):
        if (field.data != self.user.email
                and User.query.filter_by(email=field.data).first()):

            raise ValidationError('Correo ya en uso.')

    def validate_username(self, field):
        if (field.data != self.user.username
                and User.query.filter_by(username=field.data).first()):

            raise ValidationError('Nombre ya en uso.')


class CreateAccountForm(FlaskForm):
    name = StringField(
            'Cuenta',
            validators=[
                DataRequired(), Length(1, 64),
                Regexp('^[\w _.]*$', message='Solo letras.')])

    email = StringField(
            'Email',
            validators=[Length(1, 64), Email()])

    phone = StringField(
            'Telefono',
            validators=[
                Length(0, 30),
                Regexp('^[\w \(\)_.-]*$', message='Solo letras o numeros.')])

    account_type = SelectField('Tipo', coerce=int)

    contact_type = SelectField('Contacto', coerce=int)

    credit_type = SelectField('Credito', coerce=int)

    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(CreateAccountForm, self).__init__(*args, **kwargs)

        self.account_type.choices = [
            (ac_type.id, ac_type.name)
            for ac_type in Account_type.query.order_by(
                                            Account_type.name).all()]

        self.contact_type.choices = [
            (ac_type.id, ac_type.name)
            for ac_type in Account_contact_type.query.order_by(
                                            Account_contact_type.name).all()]

        self.credit_type.choices = [
            (ac_type.id, ac_type.name)
            for ac_type in Account_credit.query.order_by(
                                            Account_credit.name).all()]


class CreateSearchForm(FlaskForm):
    search_type = SelectField('Tipo', coerce=int)

    parameter = StringField(
        'Busqueda',
        validators=[
            DataRequired(),
            Length(1, 100),
            Regexp('^[\w _.,@]*$', message='Solo letras y numeros.')])

    submit = SubmitField('Buscar')

    def __init__(self, choices, *args, **kwargs):
        super(CreateSearchForm, self).__init__(*args, **kwargs)

        # Choices is a list with the options for the search form
        # Example: choices = [(1, "Nombre"), (2, "Correo")]
        self.search_type.choices = choices


class CreateNewOptionForm(FlaskForm):
    parameter = StringField(
        'Valor',
        validators=[
            DataRequired(),
            Length(1, 100),
            Regexp('^[\w _.,@]*$', message='Solo letras y numeros.')])

    submit = SubmitField('Salvar')


class CreateAddressForm(FlaskForm):
    street = StringField(
                'Calle con numero',
                validators=[
                    DataRequired(),
                    Length(1, 64),
                    Regexp('^[\w -_.#]*$', message='Solo letras.')])

    city = StringField(
                'Ciudad',
                validators=[
                    Length(1, 64),
                    Regexp('^[\w -_.#]*$', message='Solo letras.')])

    state = StringField(
                'Estado',
                validators=[
                    Length(1, 64),
                    Regexp('^[\w -_.#]*$', message='Solo letras.')])

    code = StringField(
                'Codigo postal',
                validators=[Length(0, 20)])

    country = StringField(
                'Pais',
                validators=[Length(0, 30)])

    phone = StringField(
                'Telefono',
                validators=[
                    Length(0, 30),
                    Regexp(
                        '^[\w \(\)_.-]*$',
                        message='Solo letras o numeros.')])

    description = StringField('Comentario', validators=[Length(0, 64)])

    address_type = SelectField('Tipo', coerce=int)

    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(CreateAddressForm, self).__init__(*args, **kwargs)

        self.address_type.choices = [
            (ac_type.id, ac_type.name)
            for ac_type in Account_address_type.query.order_by(
                Account_address_type.name).all()]


class CreateDataForm(FlaskForm):
    data_type = SelectField('Tipo', coerce=int)

    info = StringField(
                'Informacion',
                validators=[
                    DataRequired(), Length(1, 100)])

    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(CreateDataForm, self).__init__(*args, **kwargs)

        self.data_type.choices = [
            (ac_type.id, ac_type.name)
            for ac_type in Account_data_type.query.order_by(
                Account_data_type.name).all()]


class CreateCommentForm(FlaskForm):
    body = TextAreaField('Comentario', validators=[DataRequired()])

    submit = SubmitField('Salvar')


class CreateActivityForm(FlaskForm):
    activity_type = SelectField('Tipo', coerce=int)

    title = StringField(
                'Titulo',
                validators=[
                    DataRequired(),
                    Length(1, 60),
                    Regexp('^[\w -_.,]*$', message='Solo letras.')])

    start_date = DateTimeField(
                'Fecha de inicio',
                validators=[DataRequired()],
                format='%d/%m/%Y')

    end_date = DateTimeField(
                'Fecha de terminacion',
                validators=[DataRequired()],
                format='%d/%m/%Y')

    body = TextAreaField(
                'Descripcion',
                validators=[
                    Regexp('^[\w -_.,]*$', message='Solo letras.')])

    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(CreateActivityForm, self).__init__(*args, **kwargs)

        self.activity_type.choices = [
            (ac_type.id, ac_type.name)
            for ac_type in Account_activity_type.query.order_by(
                Account_activity_type.name).all()]

    def validate_end_date(self, field):
        if (self.start_date.data > field.data):
            raise ValidationError(
                    'Fecha final debe de ser mayor a fecha de inicio')


class CreateHcomplexForm(FlaskForm):
    name = StringField(
            'Nombre',
            validators=[
                DataRequired(), Length(1, 64),
                Regexp('^[\w -_.]*$', message='Solo letras.')])

    address = StringField(
            'Direccion',
            validators=[
                Length(0, 30),
                Regexp('^[\w \(\)_.-]*$', message='Solo letras o numeros.')])

    city = StringField(
            'Ciudad',
            validators=[
                DataRequired(), Length(1, 64),
                Regexp('^[\w _.]*$', message='Solo letras.')])

    state = StringField(
            'Estado',
            validators=[
                DataRequired(), Length(1, 64),
                Regexp('^[\w _.]*$', message='Solo letras.')])

    country = StringField(
            'Pais',
            validators=[
                DataRequired(), Length(1, 64),
                Regexp('^[\w _.]*$', message='Solo letras.')])

    zipcode = StringField(
            'Codigo Postal',
            validators=[
                DataRequired(), Length(1, 64),
                Regexp('^[\w _.]*$', message='Solo letras.')])

    submit = SubmitField('Salvar')


class CreateHouseForm(FlaskForm):
    name = StringField(
            'Nombre',
            validators=[
                DataRequired(), Length(1, 64),
                Regexp('^[\w -_.]*$', message='Solo letras.')])

    address = StringField(
            'Direccion',
            validators=[
                Length(0, 30),
                Regexp('^[\w \(\)_.-]*$', message='Solo letras o numeros.')])

    cuv = StringField(
            'CUV',
            validators=[
                Length(0, 30),
                Regexp('^[\w \(\)_.-]*$', message='Solo letras o numeros.')])

    price = StringField(
            'Precio',
            validators=[
                Length(0, 30),
                Regexp('^[\d .,]*$', message='Solo Numeros.')])

    house_status = SelectField('Estado', coerce=int)

    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(CreateHouseForm, self).__init__(*args, **kwargs)

        self.house_status.choices = [
            (ac_type.id, ac_type.name)
            for ac_type in House_status.query.order_by(
                House_status.name).all()]
