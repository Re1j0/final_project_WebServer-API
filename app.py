import os
from datetime import datetime

from config import link
from flask import Flask, render_template, send_from_directory
from flask import jsonify, redirect, url_for, flash, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import DataRequired, Length, EqualTo

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/fonts/'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


def get_all_fonts():
    font_dir = 'static/fonts/'
    font_files = []

    for filename in os.listdir(font_dir):
        if filename.endswith(('.ttf', '.otf', '.woff', '.woff2')):
            file_path = os.path.join(font_dir, filename)
            file_size = os.path.getsize(file_path) / 1024
            font_files.append({'name': filename, 'size': round(file_size, 2)})
    if True:
        return font_files
    form = UploadFontForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            font_file = form.font_file.data
            if not font_file or font_file.filename == '':
                flash('Не выбран файл для загрузки', 'danger')
                app.logger.error('Attempt to upload empty file')
                return redirect(url_for('upload'))

            filename = secure_filename(font_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            allowed_extensions = {'.ttf', '.otf', '.woff', '.woff2'}
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in allowed_extensions:
                flash('Недопустимый формат файла. Разрешены: .ttf, .otf, .woff, .woff2', 'danger')
                app.logger.warning(f'Invalid file extension attempt: {file_ext}')
                return redirect(url_for('upload'))

            if os.path.exists(file_path):
                flash('Файл с таким именем уже существует', 'danger')
                app.logger.info(f'File conflict detected: {filename}')
                return redirect(url_for('upload'))

            mime_type = font_file.content_type
            valid_mime_types = ['font/ttf', 'font/otf', 'application/font-woff']
            if mime_type not in valid_mime_types:
                flash('Неверный тип файла', 'danger')
                app.logger.error(f'Invalid MIME type detected: {mime_type}')
                return redirect(url_for('upload'))

            try:
                font_file.save(file_path)
                app.logger.info(f'File saved successfully: {filename}')
            except IOError as e:
                flash('Ошибка сохранения файла', 'danger')
                app.logger.error(f'File save error: {str(e)}')
                return redirect(url_for('upload'))

            try:
                new_font = Font(
                    filename=filename,
                    original_filename=font_file.filename,
                    user_id=current_user.id,
                    file_size=os.path.getsize(file_path),
                    upload_ip=request.remote_addr
                )
                db.session.add(new_font)
                current_user.uploads_count = Font.query.filter_by(user_id=current_user.id).count()
                db.session.commit()
                app.logger.info(f'New font record created: ID {new_font.id}')

            except SQLAlchemyError as e:
                db.session.rollback()
                flash('Ошибка базы данных', 'danger')
                app.logger.critical(f'Database error: {str(e)}')
                return redirect(url_for('upload'))
            except Exception as e:
                app.logger.warning(f'Thumbnail generation failed: {str(e)}')

            flash('Шрифт успешно опубликован', 'success')
            app.logger.info(f'User #{current_user.id} uploaded font: {filename}')

            return redirect(url_for('font_detail', font_id=new_font.id))

        except Exception as e:
            flash('Произошла непредвиденная ошибка', 'danger')
            app.logger.error(f'Upload process error: {str(e)}')
            return redirect(url_for('upload'))

    app.logger.info(f'User #{current_user.id} accessed upload page')

    return render_template(
        'upload.html',
        form=form,
        user_uploads=Font.query.filter_by(user_id=current_user.id).count(),
        storage_quota=current_user.storage_quota,
        remaining_space=current_user.get_remaining_space(),
        latest_uploads=Font.query.order_by(Font.upload_date.desc()).limit(5).all()
    )


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)


class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=25)])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm_password = PasswordField('Подтверждение пароля', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Регистрация')


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class UploadFontForm(FlaskForm):
    font_file = FileField('Файл', validators=[DataRequired()])
    submit = SubmitField('Опубликовать')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/fonts')
def fonts():
    font_files = get_all_fonts()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    total_fonts = len(font_files)
    start = (page - 1) * per_page
    end = start + per_page
    fonts_to_display = font_files[start:end][::-1]

    return render_template('fonts.html', font_files=fonts_to_display, page=page, total_fonts=total_fonts,
                           per_page=per_page)
    form = UploadFontForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            font_file = form.font_file.data
            if not font_file or font_file.filename == '':
                flash('Не выбран файл для загрузки', 'danger')
                app.logger.error('Attempt to upload empty file')
                return redirect(url_for('upload'))

            filename = secure_filename(font_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            allowed_extensions = {'.ttf', '.otf', '.woff', '.woff2'}
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in allowed_extensions:
                flash('Недопустимый формат файла. Разрешены: .ttf, .otf, .woff, .woff2', 'danger')
                app.logger.warning(f'Invalid file extension attempt: {file_ext}')
                return redirect(url_for('upload'))

            if os.path.exists(file_path):
                flash('Файл с таким именем уже существует', 'danger')
                app.logger.info(f'File conflict detected: {filename}')
                return redirect(url_for('upload'))

            mime_type = font_file.content_type
            valid_mime_types = ['font/ttf', 'font/otf', 'application/font-woff']
            if mime_type not in valid_mime_types:
                flash('Неверный тип файла', 'danger')
                app.logger.error(f'Invalid MIME type detected: {mime_type}')
                return redirect(url_for('upload'))

            try:
                font_file.save(file_path)
                app.logger.info(f'File saved successfully: {filename}')
            except IOError as e:
                flash('Ошибка сохранения файла', 'danger')
                app.logger.error(f'File save error: {str(e)}')
                return redirect(url_for('upload'))

            try:
                new_font = Font(
                    filename=filename,
                    original_filename=font_file.filename,
                    user_id=current_user.id,
                    file_size=os.path.getsize(file_path),
                    upload_ip=request.remote_addr
                )
                db.session.add(new_font)
                current_user.uploads_count = Font.query.filter_by(user_id=current_user.id).count()
                db.session.commit()
                app.logger.info(f'New font record created: ID {new_font.id}')

            except SQLAlchemyError as e:
                db.session.rollback()
                flash('Ошибка базы данных', 'danger')
                app.logger.critical(f'Database error: {str(e)}')
                return redirect(url_for('upload'))
            except Exception as e:
                app.logger.warning(f'Thumbnail generation failed: {str(e)}')

            flash('Шрифт успешно опубликован', 'success')
            app.logger.info(f'User #{current_user.id} uploaded font: {filename}')

            return redirect(url_for('font_detail', font_id=new_font.id))

        except Exception as e:
            flash('Произошла непредвиденная ошибка', 'danger')
            app.logger.error(f'Upload process error: {str(e)}')
            return redirect(url_for('upload'))

    app.logger.info(f'User #{current_user.id} accessed upload page')

    return render_template(
        'upload.html',
        form=form,
        user_uploads=Font.query.filter_by(user_id=current_user.id).count(),
        storage_quota=current_user.storage_quota,
        remaining_space=current_user.get_remaining_space(),
        latest_uploads=Font.query.order_by(Font.upload_date.desc()).limit(5).all()
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return render_template('already_authenticated.html', current_year=datetime.now().year)

    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Имя пользователя уже существует. Пожалуйста, выберите другое.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=form.username.data, password=generate_password_hash(form.password.data))
        db.session.add(new_user)
        db.session.commit()

        flash(f'Аккаунт {form.username.data} создан!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('fonts'))
        else:
            flash('Такого аккаунта не существует. Проверьте имя или пароль.', 'danger')

    return render_template('login.html', form=form)
    form = UploadFontForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            font_file = form.font_file.data
            if not font_file or font_file.filename == '':
                flash('Не выбран файл для загрузки', 'danger')
                app.logger.error('Attempt to upload empty file')
                return redirect(url_for('upload'))

            filename = secure_filename(font_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            allowed_extensions = {'.ttf', '.otf', '.woff', '.woff2'}
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in allowed_extensions:
                flash('Недопустимый формат файла. Разрешены: .ttf, .otf, .woff, .woff2', 'danger')
                app.logger.warning(f'Invalid file extension attempt: {file_ext}')
                return redirect(url_for('upload'))

            if os.path.exists(file_path):
                flash('Файл с таким именем уже существует', 'danger')
                app.logger.info(f'File conflict detected: {filename}')
                return redirect(url_for('upload'))

            mime_type = font_file.content_type
            valid_mime_types = ['font/ttf', 'font/otf', 'application/font-woff']
            if mime_type not in valid_mime_types:
                flash('Неверный тип файла', 'danger')
                app.logger.error(f'Invalid MIME type detected: {mime_type}')
                return redirect(url_for('upload'))

            try:
                font_file.save(file_path)
                app.logger.info(f'File saved successfully: {filename}')
            except IOError as e:
                flash('Ошибка сохранения файла', 'danger')
                app.logger.error(f'File save error: {str(e)}')
                return redirect(url_for('upload'))

            try:
                new_font = Font(
                    filename=filename,
                    original_filename=font_file.filename,
                    user_id=current_user.id,
                    file_size=os.path.getsize(file_path),
                    upload_ip=request.remote_addr
                )
                db.session.add(new_font)
                current_user.uploads_count = Font.query.filter_by(user_id=current_user.id).count()
                db.session.commit()
                app.logger.info(f'New font record created: ID {new_font.id}')

            except SQLAlchemyError as e:
                db.session.rollback()
                flash('Ошибка базы данных', 'danger')
                app.logger.critical(f'Database error: {str(e)}')
                return redirect(url_for('upload'))
            except Exception as e:
                app.logger.warning(f'Thumbnail generation failed: {str(e)}')

            flash('Шрифт успешно опубликован', 'success')
            app.logger.info(f'User #{current_user.id} uploaded font: {filename}')

            return redirect(url_for('font_detail', font_id=new_font.id))

        except Exception as e:
            flash('Произошла непредвиденная ошибка', 'danger')
            app.logger.error(f'Upload process error: {str(e)}')
            return redirect(url_for('upload'))

    app.logger.info(f'User #{current_user.id} accessed upload page')

    return render_template(
        'upload.html',
        form=form,
        user_uploads=Font.query.filter_by(user_id=current_user.id).count(),
        storage_quota=current_user.storage_quota,
        remaining_space=current_user.get_remaining_space(),
        latest_uploads=Font.query.order_by(Font.upload_date.desc()).limit(5).all()
    )


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта.', 'success')
    return redirect(url_for('home'))


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadFontForm()
    if form.validate_on_submit():
        font_file = form.font_file.data
        font_file.save(os.path.join(app.config['UPLOAD_FOLDER'], font_file.filename))
        flash('Шрифт опубликован.', 'success')
        return redirect(url_for('fonts'))

    return render_template('upload.html', form=form)
    form = UploadFontForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            font_file = form.font_file.data
            if not font_file or font_file.filename == '':
                flash('Не выбран файл для загрузки', 'danger')
                app.logger.error('Attempt to upload empty file')
                return redirect(url_for('upload'))

            filename = secure_filename(font_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            allowed_extensions = {'.ttf', '.otf', '.woff', '.woff2'}
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in allowed_extensions:
                flash('Недопустимый формат файла. Разрешены: .ttf, .otf, .woff, .woff2', 'danger')
                app.logger.warning(f'Invalid file extension attempt: {file_ext}')
                return redirect(url_for('upload'))

            if os.path.exists(file_path):
                flash('Файл с таким именем уже существует', 'danger')
                app.logger.info(f'File conflict detected: {filename}')
                return redirect(url_for('upload'))

            mime_type = font_file.content_type
            valid_mime_types = ['font/ttf', 'font/otf', 'application/font-woff']
            if mime_type not in valid_mime_types:
                flash('Неверный тип файла', 'danger')
                app.logger.error(f'Invalid MIME type detected: {mime_type}')
                return redirect(url_for('upload'))

            try:
                font_file.save(file_path)
                app.logger.info(f'File saved successfully: {filename}')
            except IOError as e:
                flash('Ошибка сохранения файла', 'danger')
                app.logger.error(f'File save error: {str(e)}')
                return redirect(url_for('upload'))

            try:
                new_font = Font(
                    filename=filename,
                    original_filename=font_file.filename,
                    user_id=current_user.id,
                    file_size=os.path.getsize(file_path),
                    upload_ip=request.remote_addr
                )
                db.session.add(new_font)
                current_user.uploads_count = Font.query.filter_by(user_id=current_user.id).count()
                db.session.commit()
                app.logger.info(f'New font record created: ID {new_font.id}')

            except SQLAlchemyError as e:
                db.session.rollback()
                flash('Ошибка базы данных', 'danger')
                app.logger.critical(f'Database error: {str(e)}')
                return redirect(url_for('upload'))
            except Exception as e:
                app.logger.warning(f'Thumbnail generation failed: {str(e)}')

            flash('Шрифт успешно опубликован', 'success')
            app.logger.info(f'User #{current_user.id} uploaded font: {filename}')

            return redirect(url_for('font_detail', font_id=new_font.id))

        except Exception as e:
            flash('Произошла непредвиденная ошибка', 'danger')
            app.logger.error(f'Upload process error: {str(e)}')
            return redirect(url_for('upload'))

    app.logger.info(f'User #{current_user.id} accessed upload page')

    return render_template(
        'upload.html',
        form=form,
        user_uploads=Font.query.filter_by(user_id=current_user.id).count(),
        storage_quota=current_user.storage_quota,
        remaining_space=current_user.get_remaining_space(),
        latest_uploads=Font.query.order_by(Font.upload_date.desc()).limit(5).all()
    )


@app.route('/download/<filename>')
@login_required
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/font-count', methods=['GET'])
def get_font_count():
    try:
        files = os.listdir(path='static/fonts')
        font_files = [f for f in files if f.endswith(('.ttf', '.otf', '.woff', '.woff2'))]
        return jsonify({'count': len(font_files)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        form = UploadFontForm()
        if request.method == 'POST' and form.validate_on_submit():
            try:
                font_file = form.font_file.data
                if not font_file or font_file.filename == '':
                    flash('Не выбран файл для загрузки', 'danger')
                    app.logger.error('Attempt to upload empty file')
                    return redirect(url_for('upload'))

                filename = secure_filename(font_file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                allowed_extensions = {'.ttf', '.otf', '.woff', '.woff2'}
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in allowed_extensions:
                    flash('Недопустимый формат файла. Разрешены: .ttf, .otf, .woff, .woff2', 'danger')
                    app.logger.warning(f'Invalid file extension attempt: {file_ext}')
                    return redirect(url_for('upload'))

                if os.path.exists(file_path):
                    flash('Файл с таким именем уже существует', 'danger')
                    app.logger.info(f'File conflict detected: {filename}')
                    return redirect(url_for('upload'))

                mime_type = font_file.content_type
                valid_mime_types = ['font/ttf', 'font/otf', 'application/font-woff']
                if mime_type not in valid_mime_types:
                    flash('Неверный тип файла', 'danger')
                    app.logger.error(f'Invalid MIME type detected: {mime_type}')
                    return redirect(url_for('upload'))

                try:
                    font_file.save(file_path)
                    app.logger.info(f'File saved successfully: {filename}')
                except IOError as e:
                    flash('Ошибка сохранения файла', 'danger')
                    app.logger.error(f'File save error: {str(e)}')
                    return redirect(url_for('upload'))

                try:
                    new_font = Font(
                        filename=filename,
                        original_filename=font_file.filename,
                        user_id=current_user.id,
                        file_size=os.path.getsize(file_path),
                        upload_ip=request.remote_addr
                    )
                    db.session.add(new_font)
                    current_user.uploads_count = Font.query.filter_by(user_id=current_user.id).count()
                    db.session.commit()
                    app.logger.info(f'New font record created: ID {new_font.id}')

                except SQLAlchemyError as e:
                    db.session.rollback()
                    flash('Ошибка базы данных', 'danger')
                    app.logger.critical(f'Database error: {str(e)}')
                    return redirect(url_for('upload'))
                except Exception as e:
                    app.logger.warning(f'Thumbnail generation failed: {str(e)}')

                flash('Шрифт успешно опубликован', 'success')
                app.logger.info(f'User #{current_user.id} uploaded font: {filename}')

                return redirect(url_for('font_detail', font_id=new_font.id))

            except Exception as e:
                flash('Произошла непредвиденная ошибка', 'danger')
                app.logger.error(f'Upload process error: {str(e)}')
                return redirect(url_for('upload'))

        app.logger.info(f'User #{current_user.id} accessed upload page')

        return render_template(
            'upload.html',
            form=form,
            user_uploads=Font.query.filter_by(user_id=current_user.id).count(),
            storage_quota=current_user.storage_quota,
            remaining_space=current_user.get_remaining_space(),
            latest_uploads=Font.query.order_by(Font.upload_date.desc()).limit(5).all()
        )


@app.route('/api/search-font', methods=['GET'])
def search_font():
    query = request.args.get('query', '').lower()

    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400

    try:
        files = os.listdir(path='static/fonts')
        matching_fonts = [f for f in files if query in f.lower() and f.endswith(('.ttf', '.otf', '.woff', '.woff2'))]

        font_count = len(matching_fonts)

        if matching_fonts:
            font_links = [{'name': font, 'url': f'{link}/search/{font}'} for font in matching_fonts]
            return jsonify({
                'count': font_count,
                'search_link': f'{link}/search/{query}'
            }), 200
        else:
            return jsonify({
                'count': 0,
                'message': 'No fonts found',
                'search_link': f'{link}/search/{query}'
            }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        form = UploadFontForm()
        if request.method == 'POST' and form.validate_on_submit():
            try:
                font_file = form.font_file.data
                if not font_file or font_file.filename == '':
                    flash('Не выбран файл для загрузки', 'danger')
                    app.logger.error('Attempt to upload empty file')
                    return redirect(url_for('upload'))

                filename = secure_filename(font_file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                allowed_extensions = {'.ttf', '.otf', '.woff', '.woff2'}
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in allowed_extensions:
                    flash('Недопустимый формат файла. Разрешены: .ttf, .otf, .woff, .woff2', 'danger')
                    app.logger.warning(f'Invalid file extension attempt: {file_ext}')
                    return redirect(url_for('upload'))

                if os.path.exists(file_path):
                    flash('Файл с таким именем уже существует', 'danger')
                    app.logger.info(f'File conflict detected: {filename}')
                    return redirect(url_for('upload'))

                mime_type = font_file.content_type
                valid_mime_types = ['font/ttf', 'font/otf', 'application/font-woff']
                if mime_type not in valid_mime_types:
                    flash('Неверный тип файла', 'danger')
                    app.logger.error(f'Invalid MIME type detected: {mime_type}')
                    return redirect(url_for('upload'))

                try:
                    font_file.save(file_path)
                    app.logger.info(f'File saved successfully: {filename}')
                except IOError as e:
                    flash('Ошибка сохранения файла', 'danger')
                    app.logger.error(f'File save error: {str(e)}')
                    return redirect(url_for('upload'))

                try:
                    new_font = Font(
                        filename=filename,
                        original_filename=font_file.filename,
                        user_id=current_user.id,
                        file_size=os.path.getsize(file_path),
                        upload_ip=request.remote_addr
                    )
                    db.session.add(new_font)
                    current_user.uploads_count = Font.query.filter_by(user_id=current_user.id).count()
                    db.session.commit()
                    app.logger.info(f'New font record created: ID {new_font.id}')

                except SQLAlchemyError as e:
                    db.session.rollback()
                    flash('Ошибка базы данных', 'danger')
                    app.logger.critical(f'Database error: {str(e)}')
                    return redirect(url_for('upload'))
                except Exception as e:
                    app.logger.warning(f'Thumbnail generation failed: {str(e)}')

                flash('Шрифт успешно опубликован', 'success')
                app.logger.info(f'User #{current_user.id} uploaded font: {filename}')

                return redirect(url_for('font_detail', font_id=new_font.id))

            except Exception as e:
                flash('Произошла непредвиденная ошибка', 'danger')
                app.logger.error(f'Upload process error: {str(e)}')
                return redirect(url_for('upload'))

        app.logger.info(f'User #{current_user.id} accessed upload page')

        return render_template(
            'upload.html',
            form=form,
            user_uploads=Font.query.filter_by(user_id=current_user.id).count(),
            storage_quota=current_user.storage_quota,
            remaining_space=current_user.get_remaining_space(),
            latest_uploads=Font.query.order_by(Font.upload_date.desc()).limit(5).all()
        )


@app.route('/search/<font_name>', methods=['GET'])
def search_fonts(font_name):
    try:
        files = os.listdir('static/fonts')
        matching_fonts = [f for f in files if
                          font_name.lower() in f.lower() and f.endswith(('.ttf', '.otf', '.woff', '.woff2'))]

        font_files = matching_fonts
        page = request.args.get('page', 1, type=int)
        per_page = 10
        total_fonts = len(font_files)
        start = (page - 1) * per_page
        end = start + per_page
        fonts_to_display = font_files[start:end]

        return render_template('search.html', font_files=fonts_to_display, page=page, total_fonts=total_fonts,
                               per_page=per_page)
        form = UploadFontForm()
        if request.method == 'POST' and form.validate_on_submit():
            try:
                font_file = form.font_file.data
                if not font_file or font_file.filename == '':
                    flash('Не выбран файл для загрузки', 'danger')
                    app.logger.error('Attempt to upload empty file')
                    return redirect(url_for('upload'))

                filename = secure_filename(font_file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                allowed_extensions = {'.ttf', '.otf', '.woff', '.woff2'}
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in allowed_extensions:
                    flash('Недопустимый формат файла. Разрешены: .ttf, .otf, .woff, .woff2', 'danger')
                    app.logger.warning(f'Invalid file extension attempt: {file_ext}')
                    return redirect(url_for('upload'))

                if os.path.exists(file_path):
                    flash('Файл с таким именем уже существует', 'danger')
                    app.logger.info(f'File conflict detected: {filename}')
                    return redirect(url_for('upload'))

                mime_type = font_file.content_type
                valid_mime_types = ['font/ttf', 'font/otf', 'application/font-woff']
                if mime_type not in valid_mime_types:
                    flash('Неверный тип файла', 'danger')
                    app.logger.error(f'Invalid MIME type detected: {mime_type}')
                    return redirect(url_for('upload'))

                try:
                    font_file.save(file_path)
                    app.logger.info(f'File saved successfully: {filename}')
                except IOError as e:
                    flash('Ошибка сохранения файла', 'danger')
                    app.logger.error(f'File save error: {str(e)}')
                    return redirect(url_for('upload'))

                try:
                    new_font = Font(
                        filename=filename,
                        original_filename=font_file.filename,
                        user_id=current_user.id,
                        file_size=os.path.getsize(file_path),
                        upload_ip=request.remote_addr
                    )
                    db.session.add(new_font)
                    current_user.uploads_count = Font.query.filter_by(user_id=current_user.id).count()
                    db.session.commit()
                    app.logger.info(f'New font record created: ID {new_font.id}')

                except SQLAlchemyError as e:
                    db.session.rollback()
                    flash('Ошибка базы данных', 'danger')
                    app.logger.critical(f'Database error: {str(e)}')
                    return redirect(url_for('upload'))
                except Exception as e:
                    app.logger.warning(f'Thumbnail generation failed: {str(e)}')

                flash('Шрифт успешно опубликован', 'success')
                app.logger.info(f'User #{current_user.id} uploaded font: {filename}')

                return redirect(url_for('font_detail', font_id=new_font.id))

            except Exception as e:
                flash('Произошла непредвиденная ошибка', 'danger')
                app.logger.error(f'Upload process error: {str(e)}')
                return redirect(url_for('upload'))

        app.logger.info(f'User #{current_user.id} accessed upload page')

        return render_template(
            'upload.html',
            form=form,
            user_uploads=Font.query.filter_by(user_id=current_user.id).count(),
            storage_quota=current_user.storage_quota,
            remaining_space=current_user.get_remaining_space(),
            latest_uploads=Font.query.order_by(Font.upload_date.desc()).limit(5).all()
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
