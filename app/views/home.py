# In your Home Blueprint routes.py file

from flask import Blueprint, request, render_template, redirect, url_for, flash, Response, stream_with_context, jsonify
from sqlalchemy import func, case, extract
from datetime import datetime

# --- UPDATED IMPORTS ---
# Added Category, Budget, NewCategoryForm, BudgetForm to the imports
from ..app_functions import get_current_user, get_current_user_balance, user_login_required
from ..functions import generate_string
from ..forms import NewStatementForm, StatementEditForm, NewCategoryForm, BudgetForm
from ..db import db, Statements, User, Category, Budget


home = Blueprint("Home", __name__)


@home.route("/")
@user_login_required
def home_index():
    user = get_current_user()

    user_details = {}
    user_details["name"] = user.name
    user_details["account_balance"] = round(get_current_user_balance(), 2)

    statements = Statements.query.filter(Statements.user_id == user.id).order_by(
        Statements.operation_time.desc()).limit(5).all()

    user_details["statements"] = list(
        {"desc": x.description, "amount": x.amount, "at": x.operation_time, "id": x.statement_id} for x in statements
    )

    return render_template(
        "home/index.html",
        user=user_details
    )


# --- MODIFIED new_statement route ---
@home.route("/new", methods=("GET", "POST"))
@user_login_required
def new_statement():
    user = get_current_user()
    form = NewStatementForm(request.form)
    
    # Populate the category dropdown with the user's categories
    form.category.query_factory = lambda: Category.query.filter_by(user_id=user.id).all()

    if form.validate_on_submit():
        amount = form.amount.data
        description = form.description.data
        at = form.datetime_data.data
        income = form.income.data
        expense = form.expense.data

        if not income and not expense:
            flash("Cannot add statement that is neither income nor expense!", "red")
            return redirect(url_for(".new_statement"))

        amount = abs(amount)
        if expense is True:
            amount = -amount

        statement = Statements(
            description=description,
            amount=amount,
            operation_time=at,
            user_id=user.id,
            statement_id=generate_string(),
            category_id=form.category.data.id # --- NEW: Save the selected category ---
        )
        db.session.add(statement)
        db.session.commit()

        flash("Statement was added successfully.", "green")
        return redirect(url_for("Home.home_index"))

    return render_template(
        "home/new_statement.html",
        title="New statement",
        form=form
    )


# --- NEW: Category Management Routes ---
@home.route("/categories", methods=["GET", "POST"])
@user_login_required
def manage_categories():
    user = get_current_user()
    form = NewCategoryForm(request.form)
    if form.validate_on_submit():
        new_category = Category(name=form.name.data, user_id=user.id)
        db.session.add(new_category)
        db.session.commit()
        flash(f"Category '{form.name.data}' added!", "green")
        return redirect(url_for("Home.manage_categories"))
    
    categories = Category.query.filter_by(user_id=user.id).all()
    return render_template("home/categories.html", form=form, categories=categories)

@home.route("/category/delete/<int:category_id>", methods=["POST"])
@user_login_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    if category.user_id != get_current_user().id:
        flash("You cannot delete this category.", "red")
        return redirect(url_for("Home.manage_categories"))
    
    # Optional: Handle statements with this category. Here we delete them.
    # A better approach might be to reassign them to an "Uncategorized" category.
    Statements.query.filter_by(category_id=category_id).delete()
    db.session.delete(category)
    db.session.commit()
    flash(f"Category '{category.name}' and its statements deleted.", "green")
    return redirect(url_for("Home.manage_categories"))


# --- NEW: Budgeting Routes ---
@home.route("/budgets", methods=["GET", "POST"])
@user_login_required
def manage_budgets():
    user = get_current_user()
    form = BudgetForm(request.form)
    
    # Populate the category dropdown for the form
    form.category.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=user.id).all()]

    if form.validate_on_submit():
        # Check if a budget for this category already exists and update it, or create a new one
        existing_budget = Budget.query.filter_by(user_id=user.id, category_id=form.category.data).first()
        if existing_budget:
            existing_budget.amount = form.amount.data
            flash(f"Budget for '{existing_budget.category.name}' updated!", "green")
        else:
            new_budget = Budget(user_id=user.id, category_id=form.category.data, amount=form.amount.data)
            db.session.add(new_budget)
            flash(f"Budget set for '{new_budget.category.name}'!", "green")
        db.session.commit()
        return redirect(url_for("Home.manage_budgets"))

    # --- Data for the dashboard ---
    budgets_data = []
    budgets = Budget.query.filter_by(user_id=user.id).all()
    for budget in budgets:
        # Calculate spending in the current month for this category
        start_of_month = datetime(datetime.now().year, datetime.now().month, 1)
        
        spent = db.session.query(func.sum(Statements.amount)).filter(
            Statements.user_id == user.id,
            Statements.category_id == budget.category_id,
            Statements.amount < 0, # Only expenses
            Statements.operation_time >= start_of_month
        ).scalar() or 0.0
        
        budgets_data.append({
            "category_name": budget.category.name,
            "budget_amount": budget.amount,
            "spent_amount": abs(spent),
            "remaining": budget.amount - abs(spent)
        })

    return render_template("home/budgets.html", form=form, budgets_data=budgets_data)


# --- UNCHANGED ROUTES (statements, specific_statement, download-statements) ---
# You can keep these as they are in your original file.

@home.route("/statements")
@user_login_required
def statements():
    try:
        page = int(request.args.get("page", "0"))
    except:
        page = 0
    finally:
        if page < 0:
            page = 0

    page_size = 6

    user = get_current_user()

    if request.args.get("t") == "expense":
        statements = Statements.query.filter(Statements.user_id == user.id, Statements.amount < 0).order_by(
            Statements.operation_time.desc()).limit(page_size).offset(page_size * page).all()
    elif request.args.get("t") == "income":
        statements = Statements.query.filter(Statements.user_id == user.id, Statements.amount >= 0).order_by(
            Statements.operation_time.desc()).limit(page_size).offset(page_size * page).all()
    else:
        statements = Statements.query.filter(Statements.user_id == user.id).order_by(
            Statements.operation_time.desc()).limit(page_size).offset(page_size * page).all()

    statements = list(
        {"desc": x.description, "amount": x.amount, "at": str(x.operation_time), "id": x.statement_id} for x in statements
    )

    current_balance = get_current_user_balance()
    total_expense = Statements.query.with_entities(func.sum(Statements.amount)).filter(
        Statements.user_id == user.id, Statements.amount < 0).first()[0]
    if total_expense is None:
        total_expense = 0.0
    total_expense = abs(total_expense)
    total_income = Statements.query.with_entities(func.sum(Statements.amount)).filter(
        Statements.user_id == user.id, Statements.amount >= 0).first()[0]
    if total_income is None:
        total_income = 0.0

    if request.args.get("__a") == "1":
        return statements

    date = []
    expense_amount = []
    income_amount = []
    amount = []

    for x in Statements.query.filter(Statements.user_id == user.id).order_by(Statements.operation_time).all():
        date.append(x.operation_time)
        money = x.amount

        amount.append(abs(money))

        if money < 0:
            expense_amount.append(abs(money))
            income_amount.append(None)
        else:
            income_amount.append(money)
            expense_amount.append(None)

    return render_template(
        "home/statements.html",
        title="All statements",
        statements=statements,
        total_income=total_income,
        total_expense=total_expense,
        current_balance=current_balance,
        page_size=page_size,
        round=round
    )


@home.route("/statement/<statement_id>", methods=("GET", "POST"))
@user_login_required
def specific_statement(statement_id):
    statement = Statements.query.filter(Statements.statement_id == statement_id).first_or_404()

    form = StatementEditForm(request.form)

    if form.validate_on_submit():
        amount = form.amount.data
        description = form.description.data
        date_time = form.datetime_data.data

        income = form.income.data
        expense = form.expense.data
        delete = form.delete_statement.data

        amount = abs(amount)

        if income is True:
            statement.amount = amount
            statement.description = description
            statement.operation_time = date_time

            db.session.commit()

            flash("Updated statement as income successfully", "green")

        elif expense is True:
            statement.amount = -amount
            statement.description = description
            statement.operation_time = date_time

            db.session.commit()

            flash("Updated statement as expense successfully", "green")

        elif delete is True:
            db.session.delete(statement)
            db.session.commit()

            flash("The statement was deleted successfully", "green")

            return redirect(url_for(".home_index"))

        else:
            flash("Unsupported action to perform!", "red")

        return redirect(url_for(".specific_statement", statement_id=statement_id))

    form.amount.data = abs(statement.amount)
    form.description.data = statement.description
    form.datetime_data.data = statement.operation_time

    return render_template(
        "home/statement.html",
        title="Statement",
        form=form,
        statement_id=statement_id
    )


@home.route("/download-statements")
@user_login_required
def download_statements():
    user = get_current_user()
    statements = Statements.query.filter(Statements.user_id == user.id)

    content_disposition = "attachment; filename={}'s-statements.csv".format(user.name)

    def data():
        first_iter = True
        for statement in statements.yield_per(5):
            if first_iter is True:
                first_iter = False
                yield "amount, description, datetime, type\n"

            if statement.amount < 0:
                statement_type = "expense"
            else:
                statement_type = "income"
            yield f"{abs(statement.amount)},{statement.description},{statement.operation_time.isoformat()},{statement_type}\n"

    return Response(stream_with_context(data()), 200, mimetype="text/csv", headers={
        "Content-Disposition": content_disposition
    })


# --- MODIFIED chart_data route ---
@home.route("/chart-data")
@user_login_required
def chart_data():
    user = get_current_user()

    # Group by Year-Month, sum income and expense separately
    monthly_data = db.session.query(
        func.strftime("%Y-%m", Statements.operation_time).label("month"),
        func.sum(case([(Statements.amount >= 0, Statements.amount)], else_=0)).label("income"),
        func.sum(case([(Statements.amount < 0, Statements.amount)], else_=0)).label("expense")
    ).filter(Statements.user_id == user.id).group_by("month").order_by("month").all()

    months = [row.month for row in monthly_data]
    incomes = [round(row.income or 0, 2) for row in monthly_data]
    expenses = [abs(round(row.expense or 0, 2)) for row in monthly_data]

    # --- NEW: Budget vs Actual Data ---
    budgets = db.session.query(Budget, Category).join(Category).filter(Budget.user_id == user.id).all()
    budget_labels = []
    budget_amounts = []
    actual_spending = []

    for budget, category in budgets:
        start_of_month = datetime(datetime.now().year, datetime.now().month, 1)
        spent = db.session.query(func.sum(Statements.amount)).filter(
            Statements.user_id == user.id,
            Statements.category_id == category.id,
            Statements.amount < 0,
            Statements.operation_time >= start_of_month
        ).scalar() or 0.0
        
        budget_labels.append(category.name)
        budget_amounts.append(budget.amount)
        actual_spending.append(abs(spent))

    return jsonify({
        "monthly": {
            "months": months,
            "income": incomes,
            "expense": expenses
        },
        "budget_vs_actual": {
            "labels": budget_labels,
            "budgets": budget_amounts,
            "actual": actual_spending
        }
        # We are removing the old 'expense_by_desc' as it's less useful now
    })