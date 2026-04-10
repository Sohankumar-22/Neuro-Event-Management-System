from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField,BooleanField
from wtforms.validators import DataRequired,Length,Email,Optional,EqualTo


class Signup(FlaskForm):
    username = StringField(
        "Username",
        validators = [DataRequired(),Length(5,14)]
    )

    email = StringField(
        "Email",
        validators = [DataRequired(),Email()]
    )

    password = PasswordField(
        "Password",
        validators = [DataRequired(),Length(6,11)]
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators = [DataRequired(),Length(6,11),EqualTo("password")]
    )

    submit = SubmitField("Signup")


class Login(FlaskForm):
    email = StringField(
        "Email",
        validators = [DataRequired(),Email()]
    )

    password = PasswordField(
        "Password",
        validators = [DataRequired(),Length(6,11)]
    )
   

    submit = SubmitField("Login")