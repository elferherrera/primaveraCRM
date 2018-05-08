import string
import secrets
import datetime
from flask import (render_template, flash,
                   redirect, url_for, request)
from flask_login import (current_user, login_user,
                         logout_user, login_required)
from werkzeug.urls import url_parse

from app import app, db
from app.decorators import admin_required, permission_required

from app.forms import (LoginForm, UserForm, UserAdminForm,
                       CreateAccountForm, CreateSearchForm,
                       CreateAddressForm, CreateDataForm,
                       CreateCommentForm, CreateActivityForm,
                       CreateHcomplexForm, CreateHouseForm,
                       CreateNewOptionForm, CreateSurveyForm)

from app.models import (User, Role, Permission,
                        Account, Account_type, Account_contact_type,
                        Account_address, Account_address_type,
                        Account_data, Account_data_type, Account_comment,
                        Account_activity, Account_activity_type,
                        Account_activity_comment, House_complex,
                        Account_credit, Account_survey, House, House_status)


options_list = {
    'Account_type': Account_type,
    'Account_contact_type': Account_contact_type,
    'Account_address_type': Account_address_type,
    'Account_activity_type': Account_activity_type,
    'Account_data_type': Account_data_type,
    'Account_credit': Account_credit,
    'House_status': House_status}


@app.context_processor
def include_permission_class():
    return {'Permission': Permission}


@app.route('/')
@app.route('/index')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    filter = request.args.get('filter', 'all', type=str)

    query = current_user.accounts_activities_assigned.order_by(
                        Account_activity.start_date.asc())

    if filter == 'today':
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)

        query = query.filter(
            Account_activity.start_date > today).filter(
            Account_activity.start_date < tomorrow).order_by(
                Account_activity.start_date.asc())

    elif filter == 'old':
        today = datetime.date.today()
        query = query.filter(
            Account_activity.start_date < today).order_by(
                Account_activity.start_date.asc())

    pagination = query.paginate(
                    page,
                    per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                    error_out=False)

    return render_template(
            'index.html',
            pagination=pagination)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user is None or not user.verify_password(form.password.data):
            flash('Usuario incorrecto')
            return redirect(url_for('login'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')

        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')

        return redirect(next_page)

    form.email.data = "test@test.com"
    form.password.data = ""

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/user/<int:id>/')
@login_required
def user(id):
    user = User.query.get(id)

    if user is None:
        flash("El usuario no existe")
        return redirect(url_for("index"))

    if (not current_user.can(Permission.MODERATE_ACTIVITIES) and
            user != current_user):
        flash('Los permisos que tienes no te permiten ver este usuario')
        return redirect(url_for('index'))

    nav = request.args.get('nav', 'details', type=str)
    page = request.args.get('page', 1, type=int)
    filter = request.args.get('filter', 'all', type=str)

    dictionary = {
        'id': id,
        'nav': nav,
        'filter':filter}

    query = []

    if nav == "activities":
        query = user.accounts_activities_assigned.order_by(
                            Account_activity.start_date.asc())

        if filter == 'today':
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)

            query = query.filter(
                Account_activity.start_date > today).filter(
                Account_activity.start_date < tomorrow).order_by(
                    Account_activity.start_date.asc())

        elif filter == 'old':
            today = datetime.date.today()
            query = query.filter(
                Account_activity.start_date < today).order_by(
                    Account_activity.start_date.asc())

    elif nav == "clients":
        query = user.accounts.order_by(Account.name.asc())

    elif nav == "houses":
        query = user.sold_houses

    pagination = []
    if not isinstance(query, list):
        pagination = query.paginate(
                            page,
                            per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                            error_out=False)

    return render_template(
            'user.html',
            user=user,
            dictionary=dictionary,
            pagination=pagination)


@app.route('/moduser/<int:id>/', methods=['GET', 'POST'])
@login_required
def modify_user(id):
    user = User.query.get(id)

    if user is None:
        flash("El usuario no existe")
        return redirect(url_for('index'))

    form = UserForm(user)
    if form.validate_on_submit():
        user.name = form.name.data.title()
        user.username = form.username.data.lower()
        user.email = form.email.data.lower()
        user.phone = form.phone.data
        user.location = form.location.data.title()

        if form.change_pw.data is True:
            user.password = form.password.data

        db.session.add(user)
        db.session.commit()
        flash('El usuario ha sido modificado')

        return redirect(url_for('user', id=user.id))

    form.name.data = user.name
    form.username.data = user.username
    form.email.data = user.email
    form.phone.data = user.phone
    form.location.data = user.location
    form.password.data = "aaa"
    form.password2.data = "aaa"

    return render_template(
            'data_mod.html', title="Modificar usuario", form=form)


@app.route('/users', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MODERATE_ACTIVITIES)
def users():
    page = request.args.get('page', 1, type=int)
    filter = request.args.get('filter', 'all', type=str)
    form = CreateSearchForm([(1, "Nombre"), (2, "Correo")])

    dictionary = {
        'filter': filter}

    filter_list = Role.query.order_by(Role.name.asc()).all()
    query = User.query.order_by(User.name.asc())

    if filter != "all":
        query = query.join(Role).filter(Role.name == filter)

    # If the form is validated, the query is created considering the
    # seach parameters the user introduce
    if form.validate_on_submit():
        # The option 1 is for a search by name
        if form.search_type.data == 1:
            query = User.query.filter(
                    User.name.like(
                        '%' + form.parameter.data + '%')).order_by(
                    User.name.asc())

        # The option 2 is for a search by email
        elif form.search_type.data == 2:
            query = User.query.filter(
                    User.email.like(
                        '%' + form.parameter.data + '%')).order_by(
                    User.name.asc())

    pagination = query.paginate(
                    page,
                    per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                    error_out=False)

    users = pagination.items

    return render_template(
            'users.html',
            users=users,
            form=form,
            dictionary=dictionary,
            filter_list=filter_list,
            pagination=pagination)


@app.route('/adminuser/<int:id>/', methods=['GET', 'POST'])
@login_required
@admin_required
def modify_admin(id):
    user = User.query.filter_by(id=id).first()

    if user is None:
        flash("El usuario no existe")
        return redirect(url_for('users'))

    form = UserAdminForm(user)
    if form.validate_on_submit():
        user.name = form.name.data.title()
        user.username = form.username.data.lower()
        user.email = form.email.data.lower()
        user.phone = form.phone.data
        user.location = form.location.data
        user.role = Role.query.get(form.role.data)

        db.session.add(user)
        db.session.commit()
        flash('El usuario ha sido modificado')

        return redirect(url_for('users'))

    form.name.data = user.name
    form.username.data = user.username
    form.email.data = user.email
    form.phone.data = user.phone
    form.location.data = user.location
    form.role.data = user.role_id

    return render_template(
            'data_mod.html', title="Modificar usuario", form=form)


@app.route('/adminnew', methods=['GET', 'POST'])
@login_required
@admin_required
def new_admin():
    form = UserForm()
    if form.validate_on_submit():
        user = User()

        user.name = form.name.data.title()
        user.username = form.username.data.lower()
        user.email = form.email.data.lower()
        user.phone = form.phone.data
        user.location = form.location.data
        user.password = form.password.data
        user.role = Role.query.filter_by(name="Ventas").first()

        db.session.add(user)
        db.session.commit()
        flash('El usuario ha sido creado')

        return redirect(url_for('users'))

    form.change_pw.data = True

    return render_template(
            'data_mod.html', title="Crear usuario", form=form)


@app.route('/admindelete/<int:id>/')
@login_required
@admin_required
def delete_admin(id):
    user = User.query.filter_by(id=id).first()

    if user is None:
        flash("El usuario no existe")
        return redirect(url_for('users'))

    db.session.delete(user)
    db.session.commit()
    flash("El usuario ha sido borrado")

    return redirect(url_for('users'))


@app.route('/adminpassword/<int:id>/')
@login_required
@admin_required
def password_admin(id):
    user = User.query.filter_by(id=id).first()

    if user is None:
        flash("El usuario no existe")
        return redirect(url_for('users'))

    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(alphabet) for i in range(20))

    user.password = password
    db.session.add(user)
    db.session.commit()
    flash("El password del usuario ha sido modificado por: %s" % password)

    return redirect(url_for('users'))


@app.route('/options', methods=['GET', 'POST'])
@login_required
@admin_required
def options():
    filter = request.args.get('filter', 'Account_type', type=str)
    page = request.args.get('page', 1, type=int)
    new_option = request.args.get('new_option', 0, type=int)
    edit_option = request.args.get('edit_option', 0, type=int)
    id = request.args.get('id', 0, type=int)

    dictionary = {
        'filter': filter,
        'new_option': new_option,
        'edit_option': edit_option,
        'id': id}

    form = CreateNewOptionForm()
    if form.validate_on_submit():
        option = options_list[filter]()

        if edit_option:
            option = options_list[filter].query.get(id)

            if option is None:
                return redirect(url_for('options'))

        option.name = form.parameter.data.title()

        db.session.add(option)
        db.session.commit()

        return redirect(url_for('options', filter=filter))

    query = options_list[filter].query.order_by("id")

    if edit_option:
        query = query.filter_by(id=id)

    pagination = query.paginate(
                page,
                per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                error_out=False)

    return render_template(
                'options.html',
                pagination=pagination,
                options_list=list(options_list.keys()),
                form=form,
                dictionary=dictionary)


@app.route('/options_delete/<int:id>/')
@login_required
@admin_required
def options_delete(id):
    filter = request.args.get('filter', 'Account_type', type=str)

    option = options_list[filter].query.get(id)

    if option is None:
        flash("La opcion seleccionada no existe")
        return redirect(url_for('options'))

    db.session.delete(option)
    db.session.commit()
    flash("La opcion ha sido borrada")

    return redirect(url_for('options', filter=filter))


# Accounts and details
@app.route('/accounts', methods=['GET', 'POST'])
@login_required
def accounts():
    page = request.args.get('page', 1, type=int)
    filter = request.args.get('filter', 'all', type=str)
    form = CreateSearchForm([(1, "Nombre"), (2, "Correo")])

    dictionary = {
        'filter': filter}

    filter_list = Account_type.query.order_by(Account_type.name.asc()).all()
    query = Account.query.order_by(Account.name.asc())

    if filter == "active":
        query = query.join(
                        Account_type).filter(
                        Account_type.name != "Descartado")
    elif filter != "all":
        query = query.join(Account_type).filter(Account_type.name == filter)

    # If the form is validated, the query is created considering the
    # seach parameters the user introduce
    if form.validate_on_submit():
        # The option 1 is for a search by name
        if form.search_type.data == 1:
            query = Account.query.filter(
                    Account.name.like(
                        '%' + form.parameter.data + '%')).order_by(
                    Account.name.asc())

        # The option 2 is for a search by email
        elif form.search_type.data == 2:
            query = Account.query.filter(
                    Account.email.like(
                        '%' + form.parameter.data + '%')).order_by(
                    Account.name.asc())

    pagination = query.paginate(
                    page,
                    per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                    error_out=False)
    accounts = pagination.items

    return render_template(
            'accounts.html',
            dictionary=dictionary,
            accounts=accounts,
            filter_list=filter_list,
            form=form,
            pagination=pagination)


@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_account():
    form = CreateAccountForm()

    if form.validate_on_submit():

        query = Account.query.filter(
                    Account.name.like(
                        '%' + form.name.data + '%')).first()

        if query:
            flash("No se puede guardar esta cuenta. Parece que existe un usuario con este nombre")
            return redirect(url_for('accounts'))

        query = Account.query.filter(
                    Account.phone.like(
                        '%' + form.phone.data + '%')).first()

        if query:
            flash("No se puede guardar esta cuenta. Existe una cuenta con este telefono")
            return redirect(url_for('accounts'))

        new_account = Account()
        new_account.name = form.name.data.strip().title()
        new_account.email = form.email.data.strip().lower()
        new_account.phone = form.phone.data.strip()
        new_account.type = Account_type.query.get(form.account_type.data)
        new_account.contact_type = Account_contact_type.query.get(
                                        form.contact_type.data)
        new_account.credit = Account_credit.query.get(
                                        form.credit_type.data)

        new_account.user = current_user._get_current_object()

        db.session.add(new_account)
        db.session.commit()

        return redirect(url_for('accounts'))

    form.phone.data = "1111111111"
    form.email.data = "x@x.com"

    return render_template(
        'data_mod.html',
        title="Crear nueva cuenta",
        form=form)


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_account(id):
    account = Account.query.get(id)
    if account is None:
        flash('La cuenta no existe')
        return redirect(url_for('accounts'))

    if (not current_user.can(Permission.MODERATE_ACTIVITIES) and
            account.user != current_user):
        flash('No puedes modificar una cuenta que no creaste')
        return redirect(url_for('accounts'))

    form = CreateAccountForm()

    if form.validate_on_submit():
        account.name = form.name.data.strip().title()
        account.email = form.email.data.strip().lower()
        account.phone = form.phone.data.strip()
        account.type = Account_type.query.get(form.account_type.data)
        account.contact_type = Account_contact_type.query.get(
                                    form.contact_type.data)
        account.credit = Account_credit.query.get(
                                        form.credit_type.data)

        db.session.add(account)
        db.session.commit()

        return redirect(url_for('accounts'))

    form.name.data = account.name
    form.email.data = account.email
    form.phone.data = account.phone
    form.account_type.data = account.type.id
    form.contact_type.data = account.contact_type.id
    form.credit_type.data = account.credit.id

    return render_template(
            'data_mod.html',
            title=account.name,
            form=form)


@app.route('/delete/<int:id>')
@login_required
def delete_account(id):
    account = Account.query.get(id)
    if account is None:
        flash('La cuenta no existe')
        return redirect(url_for('account.accounts'))

    if not current_user.is_administrator():
        flash('Solo administradores pueden borrar cuentas')
        return redirect(url_for('accounts'))

    db.session.delete(account)
    db.session.commit()
    flash('La cuenta ha sido eliminada')

    return redirect(url_for('accounts'))


@app.route('/account/<int:id>', methods=['GET', 'POST'])
@login_required
def account(id):
    account = Account.query.get(id)

    if account is None:
        flash('La cuenta no existe')
        return redirect(url_for('accounts'))

    if (not current_user.can(Permission.MODERATE_ACTIVITIES) and
            account.user != current_user):
        flash('No puedes ver una cuenta que no creaste')
        return redirect(url_for('accounts'))

    nav = request.args.get('nav', 'details', type=str)
    page = request.args.get('page', 1, type=int)
    page_print = request.args.get('page_print', 0, type=int)

    dictionary = {
        'id': account.id,
        'nav': nav,
        'page_print': page_print}

    query = []

    data_form = CreateDataForm()
    if data_form.validate_on_submit():
        new_data = Account_data()

        new_data.info = data_form.info.data
        new_data.type = Account_data_type.query.get(
                                data_form.data_type.data)

        new_data.account = account

        db.session.add(new_data)
        db.session.commit()
        flash('La informacion de %s se ha guardado' % new_data.type.name)

        return redirect(url_for('account', id=account.id, nav='credit'))

    comment_form = CreateCommentForm()
    if comment_form.validate_on_submit():
        new_comment = Account_comment()

        new_comment.body = comment_form.body.data
        new_comment.user = current_user._get_current_object()
        new_comment.account = account

        db.session.add(new_comment)
        db.session.commit()
        flash('El comentario se ha guardado')

        return redirect(url_for('account', id=account.id, nav='comments'))

    assign_form = CreateSearchForm([(1, "Nombre"), (2, "Correo")])
    if assign_form.validate_on_submit():
        # The option 1 is for a search by name
        if assign_form.search_type.data == 1:
            query = User.query.filter(
                    User.name.like(
                        '%' + assign_form.parameter.data + '%')).order_by(
                    User.name.asc())

        # The option 2 is for a search by email
        elif assign_form.search_type.data == 2:
            query = User.query.filter(
                    User.email.like(
                        '%' + assign_form.parameter.data + '%')).order_by(
                    User.name.asc())

    if nav == 'credit':
        query = account.data.order_by('type_id')

    elif nav == 'comments':
        query = account.comments.order_by(Account_comment.timestamp.desc())

    elif nav == 'activities':

        query = account.activities.order_by(Account_activity.timestamp.asc())

    pagination = []
    if not isinstance(query, type([])):
        pagination = query.paginate(
                    page,
                    per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                    error_out=False)

    return render_template(
                'account.html',
                account=account,
                pagination=pagination,
                data_form=data_form,
                comment_form=comment_form,
                assign_form=assign_form,
                dictionary=dictionary)


@app.route('/account_seller/<int:id>')
@login_required
def account_seller(id):
    account = Account.query.get(id)

    if account is None:
        flash('La cuenta no existe')
        return redirect(url_for('accounts'))

    seller_id = request.args.get('seller_id', '0', type=str)
    seller = User.query.get(seller_id)

    if seller is None:
        flash('El vendedor no existe')
        return redirect(url_for('account', id=account.id))

    account.user = seller
    db.session.add(account)
    db.session.commit()

    return redirect(url_for('account', id=account.id))


@app.route('/account_clear/<int:id>')
@login_required
def account_clear(id):
    account = Account.query.get(id)

    if account is None:
        flash('La cuenta no existe')
        return redirect(url_for('accounts'))

    account.user = None
    db.session.add(account)
    db.session.commit()

    return redirect(url_for('account', id=account.id))


@app.route('/account_activity/<int:id>', methods=['GET', 'POST'])
@login_required
def account_activity(id):
    activity = Account_activity.query.get(id)

    if activity is None:
        flash('La actividad no existe')
        return redirect(url_for('accounts'))

    if (not current_user.can(Permission.MODERATE_ACTIVITIES) and
            activity.account.user != current_user):
        flash('No puedes ver una cuenta que no creaste')
        return redirect(url_for('accounts'))

    page = request.args.get('page', 1, type=int)
    nav = request.args.get('nav', 'comments', type=str)

    dictionary = {
        'id': activity.id,
        'nav': nav}

    query = []

    comment_form = CreateCommentForm()
    if comment_form.validate_on_submit():
        new_comment = Account_activity_comment()

        new_comment.body = comment_form.body.data
        new_comment.user = current_user._get_current_object()
        new_comment.activity = activity

        db.session.add(new_comment)
        db.session.commit()
        flash('El comentario se ha guardado')

        return redirect(
                url_for('account_activity', id=activity.id, nav="comments"))

    search_form = CreateSearchForm([(1, "Nombre"), (2, "Correo")])
    if search_form.validate_on_submit():
        # The option 1 is for a search by name
        if search_form.search_type.data == 1:
            query = User.query.filter(
                    User.name.like(
                        '%' + search_form.parameter.data + '%')).order_by(
                    User.name.asc())

        # The option 2 is for a search by email
        elif search_form.search_type.data == 2:
            query = User.query.filter(
                    User.email.like(
                        '%' + search_form.parameter.data + '%')).order_by(
                    User.name.asc())

    if nav == "comments":
        query = activity.comments.order_by(
                    Account_activity_comment.timestamp.desc())

    elif nav == "assign" and not search_form.validate_on_submit():
        query = User.query.filter(
                User.name.like(
                    '%' + "NOPE" + '%')).order_by(
                User.name.asc())

    pagination = query.paginate(
                page,
                per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                error_out=False)

    return render_template(
                'account_activity.html',
                activity=activity,
                pagination=pagination,
                comment_form=comment_form,
                search_form=search_form,
                dictionary=dictionary)


@app.route('/account_activity_assign/<int:id>')
@login_required
def account_activity_assign(id):
    activity = Account_activity.query.get(id)

    if activity is None:
        flash('La actividad no existe')
        return redirect(url_for('accounts'))

    user_id = request.args.get('user_id', '0', type=str)
    user = User.query.get(user_id)

    if user is None:
        flash('El usuario no existe')
        return redirect(url_for('account_activity', id=activity.id))

    activity.responsable = user
    db.session.add(activity)
    db.session.commit()

    return redirect(url_for('account_activity', id=activity.id))


@app.route('/account_address/<int:id>', methods=['GET', 'POST'])
@login_required
def account_address(id):
    account = Account.query.get(id)

    if account is None:
        flash('La cuenta no existe')
        return redirect(url_for('accounts'))

    form = CreateAddressForm()

    if form.validate_on_submit():
        new_address = Account_address()

        new_address.street = form.street.data.title()
        new_address.city = form.city.data.title()
        new_address.state = form.state.data.title()
        new_address.code = form.code.data
        new_address.country = form.country.data.title()
        new_address.phone = form.phone.data
        new_address.description = form.description.data

        new_address.type = Account_address_type.query.get(
                                form.address_type.data)

        new_address.account = account

        db.session.add(new_address)
        db.session.commit()
        return redirect(url_for('account', id=account.id))

    form.street.data = "Calle"
    form.city.data = "Ciudad"
    form.state.data = "Estado"
    form.code.data = "Codigo"
    form.country.data = "Pais"
    form.phone.data = "Telefono"
    form.description.data = "Direccion de fraccionamiento"

    return render_template(
        'data_mod.html',
        title="Agregar direccion de %s" % account.name,
        form=form)


@app.route('/edit_address/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_address(id):
    address = Account_address.query.get(id)

    if address is None:
        flash('La direccion no existe')
        return redirect(url_for('accounts'))

    form = CreateAddressForm()

    if form.validate_on_submit():
        address.street = form.street.data.title()
        address.city = form.city.data.title()
        address.state = form.state.data.title()
        address.code = form.code.data
        address.country = form.country.data.title()
        address.phone = form.phone.data
        address.description = form.description.data

        address.type = Account_address_type.query.get(form.address_type.data)

        db.session.add(address)
        db.session.commit()

        return redirect(url_for('account', id=address.account.id))

    form.street.data = address.street
    form.city.data = address.city
    form.state.data = address.state
    form.code.data = address.code
    form.country.data = address.country
    form.phone.data = address.phone
    form.description.data = address.description
    form.address_type.data = address.type.id

    return render_template(
        'data_mod.html',
        title="Modificar direccion de %s" % address.account.name,
        form=form)


@app.route('/delete_address/<int:id>')
@login_required
def delete_address(id):
    address = Account_address.query.get(id)

    if address is None:
        flash('La direccion no existe')
        return redirect(url_for('accounts'))

    account_id = address.account.id
    db.session.delete(address)
    db.session.commit()
    flash('La direccion ha sido eliminada')

    return redirect(url_for('account', id=account_id))


@app.route('/delete_data/<int:id>')
@login_required
def delete_data(id):
    data = Account_data.query.get(id)

    if data is None:
        flash('La información no existe')
        return redirect(url_for('accounts'))

    account_id = data.account.id
    db.session.delete(data)
    db.session.commit()
    flash('La información ha sido eliminada')

    return redirect(url_for('account', id=account_id, nav='credit'))


@app.route('/delete_comment/<int:id>')
@login_required
def delete_comment(id):
    comment = Account_comment.query.get(id)

    if comment is None:
        flash('El comentario no existe')
        return redirect(url_for('accounts'))

    account_id = comment.account.id
    db.session.delete(comment)
    db.session.commit()
    flash('El comentario ha sido eliminado')

    return redirect(url_for('account', id=account_id, nav='comments'))


@app.route('/account_activity_new/<int:id>', methods=['GET', 'POST'])
@login_required
def account_activity_new(id):
    account = Account.query.get(id)

    if account is None:
        flash('La cuenta no existe')
        return redirect(url_for('accounts'))

    form = CreateActivityForm()

    if form.validate_on_submit():
        new_activity = Account_activity()

        new_activity.title = form.title.data
        new_activity.body = form.body.data

        new_activity.start_date = form.start_date.data
        new_activity.end_date = form.end_date.data

        new_activity.completed = 0

        new_activity.type = Account_activity_type.query.get(
                                form.activity_type.data)

        new_activity.account = account
        new_activity.creator = current_user._get_current_object()
        new_activity.responsable = current_user._get_current_object()

        db.session.add(new_activity)
        db.session.commit()
        flash("La actividad ha sido creada")

        return redirect(url_for('account', id=account.id, nav='activities'))

    return render_template(
                'data_mod.html',
                title="Actividad de cliente %s" % account.name,
                form=form)


@app.route('/account_activity_mod/<int:id>', methods=['GET', 'POST'])
@login_required
def account_activity_mod(id):
    activity = Account_activity.query.get(id)

    if activity is None:
        flash('La actividad no existe')
        return redirect(url_for('accounts'))

    form = CreateActivityForm()

    if form.validate_on_submit():
        activity.title = form.title.data
        activity.body = form.body.data

        activity.start_date = form.start_date.data
        activity.end_date = form.end_date.data

        activity.type = Account_activity_type.query.get(
                                form.activity_type.data)

        db.session.add(activity)
        db.session.commit()
        flash("La actividad ha sido modificada")

        return redirect(
                url_for('account', id=activity.account.id, nav='activities'))

    form.title.data = activity.title
    form.body.data = activity.body

    form.start_date.data = activity.start_date
    form.end_date.data = activity.end_date

    form.activity_type.data = activity.type.id

    return render_template(
                'data_mod.html',
                title="Actividad de cliente %s" % activity.account.name,
                form=form)


@app.route('/delete_activity/<int:id>')
@login_required
def delete_activity(id):
    activity = Account_activity.query.get(id)

    if activity is None:
        flash('La actividad no existe')
        return redirect(url_for('accounts'))

    account_id = activity.account.id
    db.session.delete(activity)
    db.session.commit()
    flash('La actividad ha sido eliminada')

    return redirect(url_for('account', id=account_id, nav='activities'))


@app.route('/delete_activity_comment/<int:id>')
@login_required
def delete_activity_comment(id):
    comment = Account_activity_comment.query.get(id)

    if comment is None:
        flash('El comentario no existe')
        return redirect(url_for('accounts'))

    activity_id = comment.activity.id
    db.session.delete(comment)
    db.session.commit()
    flash('El comentario ha sido eliminado')

    return redirect(url_for('account_activity', id=activity_id))


@app.route('/account_survey/<int:id>', methods=['GET', 'POST'])
@login_required
def account_survey(id):
    account = Account.query.get(id)

    if account is None:
        flash('La cuenta no existe')
        return redirect(url_for('accounts'))

    form = CreateSurveyForm()

    if form.validate_on_submit():

        if account.survey.first():
            flash('La cuenta ya tiene una encuesta guardada')
            return redirect(url_for('account', id=account.id, nav='survey'))

        new_survey = Account_survey()

        new_survey.age = form.age.data
        new_survey.status = form.status.data
        new_survey.children = form.children.data
        new_survey.location = form.location.data
        new_survey.info_work = form.info_work.data
        new_survey.info_ad = form.info_ad.data
        new_survey.info_purchase = form.info_purchase.data
        new_survey.info_price = form.info_price.data
        new_survey.info_house = form.info_house.data
        new_survey.info_houses = form.info_houses.data
        new_survey.comments = form.comments.data

        new_survey.account = account

        new_survey.complex = House_complex.query.get(form.house_complex.data)

        db.session.add(new_survey)
        db.session.commit()

        return redirect(url_for('account', id=account.id, nav='survey'))

    return render_template(
        'data_mod.html',
        title="Cuestionario %s" % account.name,
        form=form)


@app.route('/account_survey_edit/<int:id>', methods=['GET', 'POST'])
@login_required
def account_survey_edit(id):
    account_survey = Account_survey.query.get(id)

    if account_survey is None:
        flash('La encuesta no existe')
        return redirect(url_for('accounts'))

    form = CreateSurveyForm()

    if form.validate_on_submit():
        account_survey.age = form.age.data
        account_survey.status = form.status.data
        account_survey.children = form.children.data
        account_survey.location = form.location.data
        account_survey.info_work = form.info_work.data
        account_survey.info_ad = form.info_ad.data
        account_survey.info_purchase = form.info_purchase.data
        account_survey.info_price = form.info_price.data
        account_survey.info_house = form.info_house.data
        account_survey.info_houses = form.info_houses.data
        account_survey.comments = form.comments.data

        account_survey.complex = House_complex.query.get(form.house_complex.data)

        db.session.add(account_survey)
        db.session.commit()

        return redirect(url_for('account', id=account_survey.account.id, nav='survey'))

    form.house_complex.data = account_survey.complex.id
    form.age.data = account_survey.age
    form.status.data = account_survey.status
    form.children.data = account_survey.children
    form.location.data = account_survey.location
    form.info_work.data = account_survey.info_work
    form.info_ad.data = account_survey.info_ad
    form.info_purchase.data = account_survey.info_purchase
    form.info_price.data = account_survey.info_price
    form.info_house.data = account_survey.info_house
    form.info_houses.data = account_survey.info_houses
    form.comments.data = account_survey.comments

    return render_template(
        'data_mod.html',
        title="Cuestionario %s" % account_survey.account.name,
        form=form)


@app.route('/account_survey_delete/<int:id>')
@login_required
def account_survey_delete(id):
    account_survey = Account_survey.query.get(id)
    if account_survey is None:
        flash('La encuesta no existe')
        return redirect(url_for('account.accounts'))

    if not current_user.can(Permission.MODERATE_ACTIVITIES):
        flash('Solo moderadores pueden borrar encuestas')
        return redirect(url_for('accounts'))

    account_id = account_survey.account.id
    db.session.delete(account_survey)
    db.session.commit()
    flash('La encuesta ha sido eliminada')

    return redirect(url_for('account', id=account_id))


@app.route('/account_surveys')
@login_required
def account_surveys():
    page = request.args.get('page', 1, type=int)

    query = Account_survey.query.join(Account).order_by(Account.name.asc())

    pagination = query.paginate(
                    page,
                    per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                    error_out=False)

    return render_template(
            'surveys.html',
            pagination=pagination)


# House complex and houses details
@app.route('/hcomplexes', methods=['GET', 'POST'])
@login_required
def hcomplexes():
    page = request.args.get('page', 1, type=int)
    form = CreateSearchForm([(1, "Nombre"), (2, "Ciudad")])

    query = House_complex.query.order_by(House_complex.name.asc())

    # If the form is validated, the query is created considering the
    # seach parameters the user introduce
    if form.validate_on_submit():
        # The option 1 is for a search by name
        if form.search_type.data == 1:
            query = House_complex.query.filter(
                    House_complex.name.like(
                        '%' + form.parameter.data + '%')).order_by(
                    House_complex.name.asc())

        # The option 2 is for a search by city
        elif form.search_type.data == 2:
            query = House_complex.query.filter(
                    House_complex.city.like(
                        '%' + form.parameter.data + '%')).order_by(
                    House_complex.name.asc())

    pagination = query.paginate(
                    page,
                    per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                    error_out=False)

    return render_template(
            'hcomplexes.html',
            form=form,
            pagination=pagination)


@app.route('/hcomplex_new', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MODERATE_ACTIVITIES)
def hcomplex_new():
    form = CreateHcomplexForm()

    if form.validate_on_submit():
        hcomplex = House_complex()

        hcomplex.name = form.name.data.title()
        hcomplex.address = form.address.data
        hcomplex.city = form.city.data.title()
        hcomplex.state = form.state.data.title()
        hcomplex.country = form.country.data.title()
        hcomplex.zipcode = form.zipcode.data

        db.session.add(hcomplex)
        db.session.commit()
        return redirect(url_for('hcomplexes'))

    form.name.data = "Calle"
    form.address.data = "Ciudad"
    form.city.data = "Estado"
    form.state.data = "Codigo"
    form.country.data = "Pais"
    form.zipcode.data = "Codigo"

    return render_template(
        'data_mod.html',
        title="Nuevo fraccionamiento",
        form=form)


@app.route('/hcomplex_edit/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MODERATE_ACTIVITIES)
def hcomplex_edit(id):
    hcomplex = House_complex.query.get(id)

    if hcomplex is None:
        flash('El fraccionamiento no existe')
        return redirect(url_for('hcomplexes'))

    form = CreateHcomplexForm()

    if form.validate_on_submit():
        hcomplex.name = form.name.data.title()
        hcomplex.address = form.address.data
        hcomplex.city = form.city.data.title()
        hcomplex.state = form.state.data.title()
        hcomplex.country = form.country.data.title()
        hcomplex.zipcode = form.zipcode.data

        db.session.add(hcomplex)
        db.session.commit()
        return redirect(url_for('hcomplexes'))

    form.name.data = hcomplex.name
    form.address.data = hcomplex.address
    form.city.data = hcomplex.city
    form.state.data = hcomplex.state
    form.country.data = hcomplex.country
    form.zipcode.data = hcomplex.zipcode

    return render_template(
        'data_mod.html',
        title=hcomplex.name,
        form=form)


@app.route('/hcomplex_delete/<int:id>')
@login_required
@permission_required(Permission.MODERATE_ACTIVITIES)
def hcomplex_delete(id):
    hcomplex = House_complex.query.get(id)

    if hcomplex is None:
        flash('El fraccionamiento no existe')
        return redirect(url_for('hcomplexes'))

    db.session.delete(hcomplex)
    db.session.commit()
    flash('El fraccionamiento ha sido eliminado')

    return redirect(url_for('hcomplexes'))


@app.route('/hcomplex_detail/<int:id>', methods=['GET', 'POST'])
@login_required
def hcomplex_detail(id):
    hcomplex = House_complex.query.get(id)

    if hcomplex is None:
        flash('El fraccionamiento no existe')
        return redirect(url_for('hcomplexes'))

    nav = request.args.get('nav', 'details', type=str)
    filter = request.args.get('filter', 'all', type=str)
    page = request.args.get('page', 1, type=int)

    dictionary = {
        'id': hcomplex.id,
        'filter': filter,
        'nav': nav}

    filter_list = House_status.query.order_by(House_status.name.asc()).all()
    query = hcomplex.houses.order_by(House.name.asc())

    form = CreateSearchForm([(1, "Casa"), (2, "CUV")])
    # If the form is validated, the query is created considering the
    # seach parameters the user introduce
    if form.validate_on_submit():
        # The option 1 is for a search by house name
        if form.search_type.data == 1:
            query = House.query.filter(
                    House.name.like(
                        '%' + form.parameter.data + '%')).order_by(
                    House.name.asc())

        # The option 2 is for a search by CUV
        elif form.search_type.data == 2:
            query = House.query.filter(
                    House.cuv.like(
                        '%' + form.parameter.data + '%')).order_by(
                    House.name.asc())

    if filter != "all":
        query = query.join(
                    House_status).filter(
                    House_status.name == filter)

    pagination = query.paginate(
                page,
                per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                error_out=False)

    return render_template(
                'hcomplex.html',
                hcomplex=hcomplex,
                form=form,
                pagination=pagination,
                filter_list=filter_list,
                dictionary=dictionary)


@app.route('/hcomplex_print/<int:id>')
@login_required
def hcomplex_print(id):
    hcomplex = House_complex.query.get(id)

    if hcomplex is None:
        flash('El fraccionamiento no existe')
        return redirect(url_for('hcomplexes'))

    filter = request.args.get('filter', 'all', type=str)

    query = hcomplex.houses.order_by(House.name.asc())

    if filter != "all":
        query = query.join(
                    House_status).filter(
                    House_status.name == filter)

    return render_template(
                'hcomplex_print.html',
                hcomplex=hcomplex,
                query=query)


@app.route('/house_new/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MODERATE_ACTIVITIES)
def house_new(id):
    hcomplex = House_complex.query.get(id)

    if hcomplex is None:
        flash('El fraccionamiento no existe')
        return redirect(url_for('hcomplexes'))

    form = CreateHouseForm()

    if form.validate_on_submit():
        house = House()

        house.name = form.name.data.title()
        house.address = form.address.data
        house.cuv = form.cuv.data
        house.price = form.price.data

        house.status = House_status.query.get(form.house_status.data)

        house.complex = hcomplex

        db.session.add(house)
        db.session.commit()
        return redirect(
            url_for('hcomplex_detail', id=hcomplex.id, nav="houses"))

    form.name.data = "Nombre"
    form.address.data = "Direccion"
    form.cuv.data = "CUV"
    form.price.data = "Precio"

    return render_template(
        'data_mod.html',
        title="Nueva casa de %s" % hcomplex.name,
        form=form)


@app.route('/house_edit/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MODERATE_ACTIVITIES)
def house_edit(id):
    house = House.query.get(id)

    if house is None:
        flash('La casa no existe')
        return redirect(url_for('hcomplexes'))

    form = CreateHouseForm()

    if form.validate_on_submit():
        house.name = form.name.data.title()
        house.address = form.address.data
        house.cuv = form.cuv.data
        house.price = form.price.data

        house.status = House_status.query.get(form.house_status.data)

        db.session.add(house)
        db.session.commit()
        return redirect(
            url_for('hcomplex_detail', id=house.complex.id, nav="houses"))

    form.name.data = house.name
    form.address.data = house.address
    form.cuv.data = house.cuv
    form.price.data = house.price

    form.house_status.data = house.status.id

    return render_template(
        'data_mod.html',
        title=house.complex.name,
        form=form)


@app.route('/house_delete/<int:id>')
@login_required
@permission_required(Permission.MODERATE_ACTIVITIES)
def house_delete(id):
    house = House.query.get(id)

    if house is None:
        flash('La casa no existe')
        return redirect(url_for('hcomplexes'))

    hcomplex = house.complex
    db.session.delete(house)
    db.session.commit()
    flash('La casa ha sido eliminada')

    return redirect(url_for('hcomplex_detail', id=hcomplex.id, nav="houses"))


@app.route('/house_detail/<int:id>', methods=['GET', 'POST'])
@login_required
def house_detail(id):
    house = House.query.get(id)

    if house is None:
        flash('La casa no existe')
        return redirect(url_for('hcomplexes'))

    nav = request.args.get('nav', 'details', type=str)
    page = request.args.get('page', 1, type=int)
    form = CreateSearchForm([(1, "Nombre"), (2, "Correo")])

    dictionary = {
        'id': house.id,
        'nav': nav}

    pagination = []
    query = []

    # If the form is validated, the query is created considering the
    # seach parameters the user introduce
    if form.validate_on_submit():

        if nav == "owner":
            # The option 1 is for a search by name
            if form.search_type.data == 1:
                query = Account.query.filter(
                        Account.name.like(
                            '%' + form.parameter.data + '%')).order_by(
                        Account.name.asc())

            # The option 2 is for a search by email
            elif form.search_type.data == 2:
                query = Account.query.filter(
                        Account.email.like(
                            '%' + form.parameter.data + '%')).order_by(
                        Account.name.asc())

        elif nav == "seller":
            # The option 1 is for a search by name
            if form.search_type.data == 1:
                query = User.query.filter(
                        User.name.like(
                            '%' + form.parameter.data + '%')).order_by(
                        User.name.asc())

            # The option 2 is for a search by email
            elif form.search_type.data == 2:
                query = User.query.filter(
                        User.email.like(
                            '%' + form.parameter.data + '%')).order_by(
                        User.name.asc())

        pagination = query.paginate(
                    page,
                    per_page=app.config['PRIMAVERA_POSTS_PER_PAGE'],
                    error_out=False)

    return render_template(
                'house.html',
                house=house,
                form=form,
                pagination=pagination,
                dictionary=dictionary)


@app.route('/house_owner/<int:id>')
@login_required
def house_owner(id):
    house = House.query.get(id)

    if house is None:
        flash('La casa no existe')
        return redirect(url_for('hcomplexes'))

    owner_id = request.args.get('owner_id', '0', type=str)
    owner = Account.query.get(owner_id)

    if owner is None:
        flash('El comprador no existe')
        return redirect(url_for('house_detail', id=house.id))

    new_status = House_status.query.filter_by(name='Apartada').first()

    if new_status:
        house.status = new_status

    new_type = Account_type.query.filter_by(name='Cliente').first()
    if new_type:
        owner.type = new_type

    house.account = owner

    # In case the owner has a user asigned
    # the user will be assigned to the house
    if owner.user:
        house.user = owner.user

    db.session.add(house)
    db.session.commit()

    return redirect(url_for('house_detail', id=house.id))


@app.route('/house_seller/<int:id>')
@login_required
def house_seller(id):
    house = House.query.get(id)

    if house is None:
        flash('La casa no existe')
        return redirect(url_for('hcomplexes'))

    seller_id = request.args.get('seller_id', '0', type=str)
    seller = User.query.get(seller_id)

    if seller is None:
        flash('El vendedor no existe')
        return redirect(url_for('house_detail', id=house.id))

    house.user = seller
    db.session.add(house)
    db.session.commit()

    return redirect(url_for('house_detail', id=house.id))


@app.route('/house_clear/<int:id>')
@login_required
def house_clear(id):
    house = House.query.get(id)

    if house is None:
        flash('La casa no existe')
        return redirect(url_for('hcomplexes'))

    clear_type = request.args.get('clear_type', 'None', type=str)

    if clear_type is None:
        flash('No se selecciono tipo de borrado ')
        return redirect(url_for('house_detail', id=house.id))

    if clear_type == "owner":

        new_status = House_status.query.filter_by(name='En venta').first()
        if new_status:
            house.status = new_status

        new_type = Account_type.query.filter_by(name='Contacto').first()
        if new_type:
            house.account.type = new_type

        house.account = None
    elif clear_type == "user":
        house.user = None

    db.session.add(house)
    db.session.commit()

    return redirect(url_for('house_detail', id=house.id))