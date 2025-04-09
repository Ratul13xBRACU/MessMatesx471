from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=200)])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=200)])
    mess_code = StringField('Mess Code', validators=[DataRequired()])
    # role = SelectField('Role', choices=[('user', 'admin'), ('user', 'admin')], validators=[DataRequired()])
    submit = SubmitField('Register')
