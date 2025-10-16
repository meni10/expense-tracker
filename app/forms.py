# In your app/forms.py file

# --- CONSOLIDATED IMPORTS ---
from flask_wtf import FlaskForm
from wtforms import (
    StringField, FloatField, SubmitField, SelectField, 
    PasswordField, TextAreaField, DateTimeLocalField, EmailField
)
from wtforms.validators import (
    Email, Length, DataRequired, NumberRange, EqualTo
)
from wtforms_sqlalchemy.fields import QuerySelectField

# --- CORRECTED IMPORT ---
# Use a single dot to import from the same package (app/)
from .db import Category


# --- AUTHENTICATION FORMS ---
class AuthForm(FlaskForm):
    email = EmailField(
        "Your email",
        validators=[
            DataRequired("Email is required!"),
            Email("Enter a valid email!"),
            Length(max=95, message="Email should not contain more than 95 characters!")
        ]
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired("Password is required!"),
            Length(8, 30, "Password should contain 8 to 30 characters.")
        ]
    )
    submit = SubmitField("Log in")


# --- STATEMENT FORMS ---
# --- MERGED NewStatementForm ---
# This combines your original detailed form with the new category field.
class NewStatementForm(FlaskForm):
    description = TextAreaField(
        "Enter description",
        validators=[
            DataRequired("Description is required!"),
            Length(5, 180, "Description can contain 5 to 180 characters.")
        ],
        render_kw={"class": "textarea-h", "rows": "2"}
    )
    amount = FloatField(
        "Enter amount",
        validators=[
            DataRequired("Amount is required!"),
            NumberRange(0.0001, 9999999999.99, "Entered amount could not be added to your statement!")
        ]
    )
    
    # --- NEW: Use QuerySelectField for categories ---
    # This will automatically populate a dropdown with the user's categories
    category = QuerySelectField(
        'Category', 
        query_factory=None, 
        get_label='name', 
        allow_blank=False, 
        validators=[DataRequired()]
    )
    
    datetime_data = DateTimeLocalField(
        "Date and Time",
        format="%Y-%m-%dT%H:%M",
        validators=[DataRequired("This field is required!")]
    )

    expense = SubmitField("Add Expense")
    income = SubmitField("Add Income")


class StatementEditForm(NewStatementForm):
    # Inherits all fields from NewStatementForm
    expense = SubmitField("Update as Expense")
    income = SubmitField("Update as Income")
    delete_statement = SubmitField(
        "Delete Statement", 
        render_kw={"class": "delete"}
    )


# --- BUDGETING FORMS ---
# --- NEW: NewCategoryForm ---
class NewCategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired()])
    submit = SubmitField("Add Category")

# --- NEW: BudgetForm ---
class BudgetForm(FlaskForm):
    # We will populate this dynamically in the route
    category = SelectField('Category', coerce=int, validators=[DataRequired()])
    amount = FloatField("Budget Amount", validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField("Set Budget")


# --- SETTINGS FORMS ---
class SettingsForm1(FlaskForm):
    name = StringField(
        "Your name",
        validators=[
            DataRequired("Cannot set empty string as the name!"),
            Length(min=5, max=45, message="Name can contain 5 to 45 characters.")
        ]
    )
    update_name = SubmitField("Update name")

class SettingsForm2(FlaskForm):
    email = EmailField("Your email", render_kw={"disabled": "true"})

class SettingsForm3(FlaskForm):
    password = PasswordField(
        "Current password",
        validators=[
            DataRequired("Current password is required!"),
            Length(8, 30, "Password should contain 8 to 30 characters.")
        ]
    )
    new_password = PasswordField(
        "New/Confirm password",
        validators=[
            DataRequired("New/Confirm Password password is required!"),
            Length(8, 30, "Password should contain 8 to 30 characters."),
        ]
    )
    update_password = SubmitField("Update password")
    delete_account = SubmitField("Delete account", render_kw={"class": "delete"})


# --- ADMIN/EDIT USER FORM ---
class EditUserForm(SettingsForm1, AuthForm):
    # Inherits fields from SettingsForm1 and AuthForm
    update_name = None
    submit = None
    
    password = PasswordField(
        "Password to update",
        validators=[Length(max=30, message="Password should contain 8 to 30 characters.")]
    )

    update_account = SubmitField("Update data")
    delete_account = SubmitField("Delete account", render_kw={"class": "delete"})

    def __init__(self, formdata=..., **kwargs):
        super().__init__(formdata, **kwargs)
        self.name.label = "Name"
        self.email.label = "Email"