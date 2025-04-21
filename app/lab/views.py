import random
import textwrap

import psycopg2
import pytz
from bahttext import bahttext
from barcode import EAN13
from barcode.writer import SVGWriter
from io import BytesIO

import numpy as np
from datetime import date

import arrow
import pandas as pd
from faker import Faker
from flask import render_template, url_for, request, flash, redirect, make_response, send_file, session, jsonify
from flask_login import login_required, current_user
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, TableStyle, Table, KeepTogether, Spacer
from sqlalchemy import func, or_, and_

from . import lab_blueprint as lab
from .forms import *
from .models import *
from app.main.models import UserLabAffil
from collections import namedtuple, defaultdict

from ..auth.models import UserCheckinRecord

from dotenv import load_dotenv
import requests
import json
import os

load_dotenv()

# Defining the host is optional and defaults to https://openapi.flowaccount.com/v1



TestOrder = namedtuple('TestOrder', ['order', 'ordered_at', 'type', 'approved_at'])

fake = Faker(['th-TH'])

import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

configuration = openapi_client.Configuration(
    host=os.getenv('FA_URL')
)

def get_access_token():



    url = f"{configuration.host}/token?Content-Type=application/x-www-form-urlencoded"

    client_id = os.getenv('FA_CLIENT_ID')
    client_secret = os.getenv('FA_CLIENT_SECRET')
    grant_type = os.getenv('FA_GRANT_TYPE')
    scope = os.getenv('FA_SCOPE')



    payload = (
        f"client_id={client_id}&"
        f"client_secret={client_secret}&"
        f"grant_type={grant_type}&"
        f"scope={scope}"
    )
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        token_data = response.json()
        return token_data["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response.text}")



@lab.route('/<int:lab_id>')
@login_required
def landing(lab_id):
    affil = UserLabAffil.query.filter_by(lab_id=lab_id, user_id=current_user.id).first()
    if not affil or not affil.approved:
        flash('You do not have a permission to enter this lab.', 'danger')
        return redirect(url_for('main.index'))
    lab = Laboratory.query.get(lab_id)
    session['lab_id'] = lab_id
    return render_template('lab/index.html', lab=lab)


@lab.route('/labs', methods=['GET', 'POST'])
@lab.route('/labs/<int:lab_id>', methods=['GET', 'POST'])
@login_required
def edit_lab(lab_id=None):
    if lab_id is None:
        form = LabForm()
    else:
        lab = Laboratory.query.get(lab_id)
        form = LabForm(obj=lab)
    if request.method == 'POST':
        if form.validate_on_submit():
            if lab_id is None:
                lab = Laboratory()
                lab.creator = current_user
            form.populate_obj(lab)
            db.session.add(lab)
            db.session.commit()
            if lab_id:
                flash('Your new lab has been created.', 'success')
                return redirect(url_for('lab.landing', lab_id=lab_id))
            else:
                flash('Your lab information has been updated.', 'success')
                return redirect(url_for('main.index'))
        else:
            flash(f'Error happened. {form.errors}', 'danger')
    return render_template('lab/lab_form.html', form=form)


@lab.route('/<int:lab_id>/tests')
@login_required
def list_tests(lab_id):
    lab = Laboratory.query.get(lab_id)
    return render_template('lab/test_list.html', lab=lab)


@lab.route('/<int:lab_id>/choice_sets')
@login_required
def list_choice_sets(lab_id):
    lab = Laboratory.query.get(lab_id)
    return render_template('lab/choice_set_list.html', lab=lab)


@lab.route('/<int:lab_id>/choice_sets/<int:choice_set_id>/items', methods=['GET', 'POST'])
@lab.route('/<int:lab_id>/choice_sets/<int:choice_set_id>/items/<int:choice_item_id>', methods=['GET', 'POST'])
@login_required
def add_choice_item(lab_id, choice_set_id, choice_item_id=None):
    if choice_item_id:
        item = LabResultChoiceItem.query.get(choice_item_id)
        form = ChoiceItemForm(obj=item)
    else:
        form = ChoiceItemForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            if not choice_item_id:
                item = LabResultChoiceItem()
            form.populate_obj(item)
            item.choice_set_id = choice_set_id
            db.session.add(item)
            # activity = LabActivity(
            #     lab_id=lab_id,
            #     actor=current_user,
            #     message='Added result choice item',
            #     detail=item.result,
            #     added_at=arrow.now('Asia/Bangkok').datetime
            # )
            # db.session.add(activity)
            db.session.commit()
            flash('New choice has been added.', 'success')
        else:
            flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('lab.list_choice_sets', lab_id=lab_id))
    return render_template('lab/new_choice_item.html', form=form)


@lab.route('/result-sets/items/<int:choice_item_id>', methods=['DELETE'])
@login_required
def remove_choice_item(choice_item_id):
    item = LabResultChoiceItem.query.get(choice_item_id)
    resp = make_response()
    if item:
        db.session.delete(item)
        db.session.commit()
    else:
        resp.headers['HX-Reswap'] = 'none'
    return resp


@lab.route('/<int:lab_id>/choice_sets/add', methods=['GET', 'POST'])
@lab.route('/<int:lab_id>/choice_sets/<int:choice_set_id>', methods=['GET', 'POST'])
@login_required
def add_choice_set(lab_id, choice_set_id=None):
    if choice_set_id:
        choice_set = LabResultChoiceSet.query.get(choice_set_id)
        form = ChoiceSetForm(obj=choice_set)
    else:
        form = ChoiceSetForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            if not choice_set_id:
                choice_set = LabResultChoiceSet()
            form.populate_obj(choice_set)
            choice_set.lab_id = lab_id
            db.session.add(choice_set)
            # activity = LabActivity(
            #     lab_id=lab_id,
            #     message='Added a new choice set',
            #     detail=choice_set.name,
            #     added_at=arrow.now('Asia/Bangkok').datetime,
            #     actor=current_user
            # )
            # db.session.add(activity)
            db.session.commit()
            flash('New choice set has been added.', 'success')
        else:
            flash('Error occurred while adding a new choice set.', 'danger')
        return redirect(url_for('lab.list_choice_sets', lab_id=lab_id))
    return render_template('lab/new_choice_set.html', form=form)


@lab.route('/<int:lab_id>/choice_sets/<int:choice_set_id>/remove')
@login_required
def remove_choice_set(lab_id, choice_set_id):
    choiceset = LabResultChoiceSet.query.get(choice_set_id)
    if choiceset:
        db.session.delete(choiceset)
        db.session.commit()
        flash('The choice set has been removed.', 'success')
    else:
        flash('The choice set does not exist.', 'warning')
    return redirect(url_for('lab.list_choice_sets', lab_id=lab_id))


@lab.route('/<int:lab_id>/quantests/add', methods=['GET', 'POST'])
@login_required
def add_test(lab_id):
    LabTestForm = create_lab_test_form(lab_id)
    form = LabTestForm(lab_id=lab_id)
    form.choice_set.query = LabResultChoiceSet.query.filter_by(lab_id=lab_id)
    if request.method == 'POST':
        if form.validate_on_submit():
            new_test = LabTest()
            form.populate_obj(new_test)
            new_test.lab_id = lab_id
            new_test.added_at = arrow.now('Asia/Bangkok').datetime
            db.session.add(new_test)
            db.session.commit()
            flash('New quantative test has been added.')
            return redirect(url_for('lab.list_tests', lab_id=lab_id))
        else:
            flash(form.errors, 'danger')
    return render_template('lab/new_test.html', form=form, lab_id=lab_id)


@lab.route('/<int:lab_id>/quantests/<int:test_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_test(lab_id, test_id):
    test = LabTest.query.get(test_id)
    LabTestForm = create_lab_test_form(lab_id)
    form = LabTestForm(obj=test)
    form.choice_set.query = LabResultChoiceSet.query.filter_by(lab_id=lab_id)
    if request.method == 'POST':
        if form.validate_on_submit():
            form.populate_obj(test)
            db.session.add(test)
            db.session.commit()
            flash('Data have been saved.', 'success')
            return redirect(url_for('lab.list_tests', lab_id=lab_id))
        else:
            flash(f'An error occurred. Please contact the system administrator.{form.errors}', 'danger')
    return render_template('lab/new_test.html', form=form, lab_id=lab_id, test=test)


@lab.route('/physical-exams/<int:order_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_physical_exam_record(order_id):
    order = LabTestOrder.query.get(order_id)
    form = LabPhysicalExamRecordForm(obj=order.physical_exam)
    if request.method == 'POST':
        if form.validate_on_submit():
            if order.physical_exam:
                record = order.physical_exam
            else:
                record = LabPhysicalExamRecord()
            form.populate_obj(record)
            record.order = order
            record.created_at = arrow.now('Asia/Bangkok').datetime
            db.session.add(record)
            db.session.commit()
        else:
            flash(f'An error occurred. Please contact the system: {form.errors}', 'danger')
        resp = make_response()
        resp.headers['HX-Refresh'] = 'true'
        return resp

    return render_template('lab/modals/physical_exam_form.html', form=form, order=order)


@lab.route('/tests/<int:test_id>/specimens/container-items', methods=['GET', 'POST'])
@lab.route('/tests/<int:test_id>/specimens/container-items/<int:container_item_id>/edit',
           methods=['GET', 'DELETE', 'PUT'])
@login_required
def edit_specimen_container_item(test_id, container_item_id=None):
    test = LabTest.query.get(test_id)
    LabSpecimenContainerItemForm = create_lab_specimen_container_item_form(test.lab_id)
    if container_item_id:
        container_item = LabSpecimenContainerItem.query.get(container_item_id)
        form = LabSpecimenContainerItemForm(obj=container_item)
    else:
        form = LabSpecimenContainerItemForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            if not container_item_id:
                _item = LabSpecimenContainerItem()
                form.populate_obj(_item)
                _item.lab_id = test.lab_id
                _item.lab_test_id = test_id
                db.session.add(_item)
                db.session.commit()
                # template = f'''
                # <tr id="container-item-{_item.id}">
                # <td>{_item.specimen_container}</td>
                # <td>{_item.volume}</td>
                # <td>{_item.note}</td>
                # <td>
                #     <a hx-get="{ url_for('lab.edit_specimen_container_item', test_id=_item.lab_test_id, container_item_id=_item.id) }"
                #        hx-target="#specimenContainerModal"
                #        hx-swap="innerHTML"
                #     >
                #     <span class="icon">
                #         <i class="fas fa-pencil-alt"></i>
                #     </span>
                #     </a>
                # </td>
                # </tr>
                # '''
                resp = make_response()
                resp.headers['HX-Refresh'] = 'true'
                return resp
        else:
            print(form.errors)
    if request.method == 'DELETE':
        db.session.delete(container_item)
        db.session.commit()
        resp = make_response()
        resp.headers['HX-Trigger-After-Swap'] = 'closeModal'
        return resp
    if request.method == 'PUT':
        if form.validate_on_submit():
            form.populate_obj(container_item)
            db.session.add(container_item)
            db.session.commit()
            template = f'''
                    <tr id="container-item-{container_item.id}">
                    <td>{container_item.specimen_container}</td>
                    <td>{container_item.volume}</td>
                    <td>{container_item.note}</td>
                    <td>
                        <a hx-get="{url_for('lab.edit_specimen_container_item', test_id=container_item.lab_test_id, container_item_id=container_item.id)}"
                           hx-target="#specimenContainerModal"
                           hx-swap="innerHTML"
                        >
                        <span class="icon">
                            <i class="fas fa-pencil-alt"></i>
                        </span>
                        </a>
                    </td>
                    </tr>
                    '''
            resp = make_response(template)
            resp.headers['HX-Trigger-After-Swap'] = 'closeModal'
            return resp
        else:
            print(form.errors)

    return render_template('lab/modals/specimen_container.html',
                           form=form,
                           test_id=test_id,
                           container_item_id=container_item_id,
                           target=f'#container-item-{container_item_id}')


@lab.route('/<int:lab_id>/quantests/<int:test_id>/remove', methods=['GET', 'POST'])
@login_required
def remove_quan_test(lab_id, test_id):
    if not current_user.is_affiliated_with(lab_id):
        flash('You do not have a permission to perform this task.', 'danger')

    test = LabTest.query.get(test_id)
    db.session.delete(test)
    db.session.commit()
    flash('The record has been removed along with its associated records.', 'success')
    return redirect(request.referrer)


@lab.route('/<int:lab_id>/customers')
@login_required
def list_patients(lab_id):
    lab = Laboratory.query.get(lab_id)
    return render_template('lab/customer_list.html', lab=lab)


def add_customer_items_from_select(fieldname, model, attribute, attrname, lab_id):
    values = request.form.getlist(fieldname)
    objs = []
    for value in values:
        obj = model.query.filter(attribute == value).filter_by(lab_id=lab_id).first()
        if not obj:
            obj = model(lab_id=lab_id)
            setattr(obj, attrname, value)
        objs.append(obj)
    return objs


@lab.route('/<int:lab_id>/patients/add', methods=['GET', 'POST'])
@lab.route('/<int:lab_id>/patients/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def add_patient(lab_id, customer_id=None):
    # TODO: use Ajax for datatable.
    LabCustomerForm = create_customer_form(lab_id)
    if customer_id:
        customer = LabCustomer.query.get(customer_id)
        form = LabCustomerForm(obj=customer)
    else:
        customer = None
        form = LabCustomerForm()
    lab = Laboratory.query.get(lab_id)
    if request.method == 'POST':
        if form.validate_on_submit():
            diseases_ = add_customer_items_from_select('underlying_diseases',
                                                       LabCustomerUnderlyingDisease,
                                                       LabCustomerUnderlyingDisease.desc,
                                                       'desc',
                                                       lab_id)
            drugs_ = add_customer_items_from_select('drug_allergies',
                                                    LabCustomerDrugAllergy,
                                                    LabCustomerDrugAllergy.drug,
                                                    'drug',
                                                    lab_id)
            meds_ = add_customer_items_from_select('medications',
                                                   LabCustomerMedication,
                                                   LabCustomerMedication.drug,
                                                   'drug',
                                                   lab_id)
            if not customer:
                customer = LabCustomer.query.filter_by(pid=form.pid.data, lab=lab).first()
                if not customer:
                    customer = LabCustomer()
                    customer.generate_hn()
                    customer.lab_id = lab_id
                else:
                    flash('The customer already registered.', 'warning')
                    return render_template('lab/new_customer.html', form=form, lab_id=lab_id)

            form.populate_obj(customer)
            customer.underlying_diseases = diseases_
            customer.drug_allergies = drugs_
            customer.medication = meds_
            db.session.add(customer)
            db.session.commit()
            if customer_id:
                flash('Customer info has been updated.', 'success')
            else:
                flash('New customer has been added.', 'success')
            return render_template('lab/customer_list.html', lab=lab)
        else:
            flash(f'Failed to add a new customer. {form.errors}', 'danger')
    return render_template('lab/new_customer.html', form=form, lab_id=lab_id, customer=customer)


@lab.route('/api/labs/<int:lab_id>/underlying_diseases')
@login_required
def get_underlying_diseases(lab_id):
    data = [{'id': d.desc, 'text': d.desc} for d in LabCustomerUnderlyingDisease.query.filter_by(lab_id=lab_id)]
    return jsonify(results=data)


@lab.route('/api/labs/<int:lab_id>/drug_allergies')
@login_required
def get_drug_allergies(lab_id):
    data = [{'id': d.drug, 'text': d.drug} for d in LabCustomerDrugAllergy.query.filter_by(lab_id=lab_id)]
    return jsonify(results=data)


@lab.route('/api/labs/<int:lab_id>/medications')
@login_required
def get_medications(lab_id):
    data = [{'id': d.drug, 'text': d.drug} for d in LabCustomerMedication.query.filter_by(lab_id=lab_id)]
    return jsonify(results=data)


@lab.route('/<int:lab_id>/patients/random', methods=['POST'])
@login_required
def add_random_patients(lab_id):
    n = request.args.get('n', 5, type=int)
    lab = Laboratory.query.get(lab_id)
    if request.method == 'POST':
        for i in range(n):
            profile = fake.profile()
            firstname, lastname = profile['name'].split(' ')
            age_ = date.today() - profile['birthdate']
            if age_.days / 365 < 15:
                if profile['sex'] == 'M':
                    title = random.choice(['เด็กชาย', 'สามเณร'])
                else:
                    title = 'เด็กหญิง'
            else:
                if profile['sex'] == 'M':
                    title = random.choice(['นาย', 'พระภิกษุ'])
                else:
                    title = random.choice(['นาง', 'นางสาว'])
            customer_ = LabCustomer(
                gender='ชาย' if profile['sex'] == 'M' else 'หญิง',
                dob=profile['birthdate'],
                firstname=firstname,
                lastname=lastname,
                title=title,
                lab=lab
            )
        # activity = LabActivity(
        #     lab_id=lab_id,
        #     actor=current_user,
        #     message='Added random customers',
        #     detail=customer_.fullname,
        #     added_at=arrow.now('Asia/Bangkok').datetime
        # )
        # db.session.add(activity)
        db.session.commit()
        flash('New random customers have been added.', 'success')
        resp = make_response()
        resp.headers['HX-Refresh'] = 'true'
        return resp


@lab.route('/<int:lab_id>/patients/<int:customer_id>/orders', methods=['GET', 'POST'])
@lab.route('/<int:lab_id>/patients/<int:customer_id>/orders/<int:order_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def add_test_order(lab_id, customer_id, order_id=None):
    lab = Laboratory.query.get(lab_id)
    referrer = request.args.get('back')
    selected_test_ids = []
    selected_profile_ids = []
    order = None
    if order_id:
        order = LabTestOrder.query.get(order_id)
        selected_test_ids = [record.test.id for record in order.active_test_records if not record.profile_id]
        selected_profile_ids = [record.profile_id for record in order.active_test_records]
    if request.method == 'DELETE':
        order.cancelled_at = arrow.now('Asia/Bangkok').datetime
        for rec in order.test_records:
            rec.cancelled = True
            db.session.add(rec)
        # activity = LabActivity(
        #     lab_id=lab_id,
        #     actor=current_user,
        #     message='Cancelled an order.',
        #     detail=order.id,
        #     added_at=arrow.now('Asia/Bangkok').datetime
        # )
        db.session.add(order)
        # db.session.add(activity)
        db.session.commit()
        resp = make_response()
        resp.headers['HX-Refresh'] = 'true'
        return resp
    if request.method == 'POST':
        form = request.form
        test_ids = [int(_id) for _id in form.getlist('test_ids')]
        profile_ids = [int(_id) for _id in form.getlist('profile_ids')]
        package_ids = [int(_id) for _id in form.getlist('package_ids')]
        selected_test_ids = set(test_ids)
        if not order_id:
            order = LabTestOrder(
                lab_id=lab_id,
                customer_id=customer_id,
                ordered_at=arrow.now('Asia/Bangkok').datetime,
                ordered_by=current_user,
                code=LabTestOrder.generate_code(),
                test_records=[LabTestRecord(test_id=tid) for tid in test_ids],
            )
            for profile_id in profile_ids:
                profile = LabTestProfile.query.get(profile_id)
                order.test_records = order.test_records.all() + [LabTestRecord(test_id=test.id, profile_id=profile_id)
                                                                 for test in profile.tests if test.id not in selected_test_ids]
                selected_test_ids.update([t.id for t in profile.tests])
            for package_id in package_ids:
                package = LabServicePackage.query.get(package_id)
                order.test_records = order.test_records.all() + [LabTestRecord(test_id=t.id, package_id=package.id)
                                                                 for t in package.tests if t.id not in selected_test_ids]
                selected_test_ids.update([t.id for t in package.tests])
                for pp in package.profiles:
                    order.test_records = order.test_records.all()\
                                         + [LabTestRecord(test_id=test.id, profile_id=pp.id, package_id=package_id)
                                            for test in pp.tests if test.id not in selected_test_ids]
                    selected_test_ids.update([t.id for t in pp.tests])
            flash('New order has been added.', 'success')
        else:
            # TODO: refactor this part for better performance
            for test_id in test_ids:
                if test_id not in selected_test_ids:
                    order.test_records.append(LabTestRecord(test_id=test_id))
            for test_id in selected_test_ids:
                test_record = LabTestRecord.query.filter_by(test_id=test_id, order_id=order_id).first()
                if test_id not in test_ids:
                    test_record.cancelled = True
                    db.session.add(test_record)
            for profile_id in profile_ids:
                if profile_id not in selected_profile_ids:
                    profile = LabTestProfile.query.get(profile_id)
                    order.test_records = order.test_records.all() + [LabTestRecord(test_id=test.id,
                                                                                   profile_id=profile_id)
                                                                     for test in profile.tests]
            for selected_profile_id in selected_profile_ids:
                if selected_profile_id not in profile_ids:
                    for test_record in order.test_records.filter_by(profile_id=selected_profile_id):
                        test_record.cancelled = True
                        db.session.add(test_record)
            flash('The order has been updated.', 'success')

        db.session.add(order)
        db.session.commit()
        return redirect(url_for('lab.show_customer_test_records',
                                customer_id=customer_id, order_id=order.id))
    return render_template('lab/new_test_order.html',
                           referrer=referrer,
                           lab=lab,
                           order=order,
                           customer_id=customer_id,
                           selected_profile_ids=selected_profile_ids,
                           selected_test_ids=selected_test_ids)


@lab.route('/orders/<int:order_id>/barcode')
@login_required
def print_order_barcode(order_id):
    order = LabTestOrder.query.get(order_id)
    containers = defaultdict(int)
    container_counts = defaultdict(int)
    barcodes = []
    for record in order.active_test_records:
        for sc in record.test.specimen_container_items:
            code = f'{order.code}{sc.specimen_container.number:02}{container_counts[sc.specimen_container.container]}'
            if containers[code] + sc.volume < sc.specimen_container.max_volume:
                containers[code] += sc.volume
            else:
                container_counts[sc.specimen_container] += 1
                code = f'{order.code}{sc.specimen_container.number:02}{container_counts[sc.specimen_container.container]}'
                containers[code] += sc.volume
    for code in containers:
        rv = BytesIO()
        _text = f'{code} {order.ordered_at.strftime("%m/%d/%Y")}'
        EAN13(code, writer=SVGWriter()).write(rv, {'module_height': 8.0, 'module_width': 0.3}, text=_text)
        barcodes.append((order, rv.getvalue().decode('utf-8')))

    docdef = {
        'pageSize': {'width': 200, 'height': 200},
        'pageMargins': [0, 0, 0, 0],
        'pageOrientation': 'portrait',
        'content': [
            {'text': 'HN09099900'},
            {'text': 'Jane Doe'},
            {'text': '2/12/2024 10:34:45'}
        ]
    }
    return render_template('lab/order_barcode.html',
                           barcodes=barcodes, order=order, docdef=docdef)


@lab.route('/<int:lab_id>/patients/<int:customer_id>/auto-orders', methods=['POST'])
@login_required
def auto_add_test_order(lab_id, customer_id):
    lab = Laboratory.query.get(lab_id)
    num_tests = LabTest.query.count()
    random_minutes = random.randint(0, 60)
    order_datetime = arrow.now('Asia/Bangkok').shift(minutes=+random_minutes)
    max_datetime = order_datetime
    tests = LabTest.query.filter_by(lab_id=lab_id) \
        .order_by(func.random()).limit(random.randint(1, num_tests))
    if request.method == 'POST':
        test_records = []
        for test in tests:
            updater = random.choice([member for member in lab.lab_members if member.approved])
            approver = random.choice([member for member in lab.lab_members if member.approved])
            test_record = LabTestRecord(test=test, updater=updater.user)
            test_records.append(test_record)
            rejected = np.random.binomial(1, 0.05, 1).sum()
            if rejected:
                random_minutes = random.randint(0, 30)
                reject_datetime = order_datetime.shift(minutes=+random_minutes)
                reject_reasons = ['สิ่งส่งตรวจไม่เหมาะสมกับการทดสอบ',
                                  'สิ่งส่งตรวจไม่เพียงพอ',
                                  'คุณภาพของสิ่งส่งตรวจไม่ดี',
                                  'ภาชนะรั่วหรือแตก',
                                  'ไม่มีรายการตรวจ',
                                  'ข้อมูลคนไข้ไม่ตรงกัน',
                                  'อื่นๆ']
                reject_record = LabOrderRejectRecord(created_at=reject_datetime.datetime,
                                                     reason=random.choice(reject_reasons),
                                                     creator_id=updater.user.id,
                                                     )
                test_record.reject_record = reject_record
                if reject_datetime > max_datetime:
                    max_datetime = reject_datetime
            else:
                random_minutes = random.randint(1, 20)
                receive_datetime = order_datetime.shift(minutes=+random_minutes)
                random_minutes = random.randint(20, 90)
                update_datetime = receive_datetime.shift(minutes=+random_minutes)
                test_record.updated_at = update_datetime.datetime
                test_record.received_at = receive_datetime.datetime
                if test.choice_set:
                    if test.choice_set.choice_items:
                        test_record.text_result = random.choice(test.choice_set.choice_items).result
                    else:
                        test_record.text_result = 'This is a mockup result.'
                else:
                    low = test.min_value if isinstance(test.min_value, int) else 10
                    high = test.max_value if isinstance(test.max_value, int) else 1000
                    test_record.num_result = random.randint(low, high)

                if update_datetime > max_datetime:
                    max_datetime = update_datetime

        random_minutes = random.randint(1, 60)
        approve_datetime = max_datetime.shift(minutes=+random_minutes)
        order = LabTestOrder(
            lab_id=lab_id,
            customer_id=customer_id,
            ordered_at=order_datetime.datetime,
            ordered_by=updater.user,
            test_records=test_records,
            approved_at=approve_datetime.datetime,
            approver=approver.user,
        )
        # activity = LabActivity(
        #     lab_id=lab_id,
        #     actor=current_user,
        #     message='Added an order.',
        #     detail=order.id,
        #     added_at=arrow.now('Asia/Bangkok').datetime
        # )
        flash('New order has been added automatically.', 'success')
        db.session.add(order)
        # db.session.add(activity)
        db.session.commit()
        resp = make_response()
        resp.headers['HX-Refresh'] = 'true'
        return resp


@lab.route('/<int:lab_id>/orders', methods=['GET', 'POST'])
@login_required
def list_test_orders(lab_id):
    lab = Laboratory.query.get(lab_id)
    return render_template('lab/test_order_list.html', lab=lab)


@lab.route('/records/<int:record_id>/cancel', methods=['POST'])
@login_required
def cancel_test_record(record_id):
    record = LabTestRecord.query.get(record_id)
    # activity = LabActivity(
    #     lab_id=record.order.lab_id,
    #     actor=current_user,
    #     message='Cancelled the test order.',
    #     detail=record.id,
    #     added_at=arrow.now('Asia/Bangkok').datetime
    # )
    record.cancelled = True
    # db.session.add(activity)
    db.session.commit()
    flash('The test has been cancelled.', 'success')

    resp = make_response()
    resp.headers['HX-Refresh'] = 'true'
    return resp


# TODO: deprecated
@lab.route('/records/<int:record_id>/reject', methods=['GET', 'POST'])
@login_required
def reject_test_order(record_id):
    record = LabTestRecord.query.get(record_id)
    form = LabOrderRejectRecordForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            new_record = LabOrderRejectRecord()
            form.populate_obj(new_record)
            new_record.created_at = arrow.now('Asia/Bangkok').datetime
            new_record.creator = current_user
            record.reject_record = new_record
            record.cancelled = True
            db.session.add(record)
            db.session.add(new_record)
            # activity = LabActivity(
            #     lab_id=record.order.lab_id,
            #     actor=current_user,
            #     message='Rejected and cancelled the test order.',
            #     detail=record.id,
            #     added_at=arrow.now('Asia/Bangkok').datetime
            # )
            # db.session.add(activity)
            db.session.commit()
            flash('The test has been rejected.', 'success')
            return redirect(url_for('lab.show_customer_test_records', customer_id=record.order.customer.id,
                                    order_id=record.order.id))
        else:
            flash('{}. Please contact the system admin.'.format(form.errors), 'danger')
    return render_template('lab/order_reject.html', form=form)


@lab.route('/records/<int:record_id>/receive', methods=['GET', 'POST'])
@login_required
def receive_test_order(record_id):
    record = LabTestRecord.query.get(record_id)
    record.received_at = arrow.now('Asia/Bangkok').datetime
    record.receiver = current_user
    db.session.add(record)
    # activity = LabActivity(
    #     lab_id=record.order.lab_id,
    #     actor=current_user,
    #     message='Received the test.',
    #     detail=record.id,
    #     added_at=arrow.now('Asia/Bangkok').datetime
    # )
    # db.session.add(activity)
    db.session.commit()
    flash('The order has been received.', 'success')
    return redirect(url_for('lab.show_customer_test_records',
                            order_id=record.order_id, customer_id=record.order.customer.id))


@lab.route('/orders/<int:order_id>/receive/all', methods=['POST'])
@login_required
def receive_all_tests(order_id):
    order = LabTestOrder.query.get(order_id)
    for record in order.test_records:
        record.received_at = arrow.now('Asia/Bangkok').datetime
        record.receiver = current_user
        db.session.add(record)
    db.session.commit()
    flash('The records has been received.', 'success')
    resp = make_response()
    resp.headers['HX-Refresh'] = 'true'
    return resp


@lab.route('/<int:lab_id>/orders/pending', methods=['GET', 'POST'])
@login_required
def list_pending_orders(lab_id):
    lab = Laboratory.query.get(lab_id)
    return render_template('lab/pending_orders.html', lab=lab)


@lab.route('/<int:lab_id>/activities')
@login_required
def list_activities(lab_id):
    lab = Laboratory.query.get(lab_id)
    return render_template('lab/log.html', lab=lab)


@lab.route('/customers/<int:customer_id>/records')
@login_required
def show_customer_records(customer_id):
    customer = LabCustomer.query.get(customer_id)
    if customer:
        return render_template('lab/customer_records.html', customer=customer)


@lab.route('/labs/<int:lab_id>/customers/<int:customer_id>/profile')
@login_required
def show_customer_profile(lab_id, customer_id):
    lab = Laboratory.query.get(lab_id)
    customer = LabCustomer.query.get(customer_id)
    if customer:
        return render_template('lab/customer_profile.html', customer=customer, lab=lab)


@lab.route('/orders/<int:order_id>/records')
@login_required
def show_customer_test_records(order_id):
    order = LabTestOrder.query.get(order_id)
    customer = order.customer
    if request.headers.get('HX-Request') == 'true':
        return render_template('lab/partials/customer_test_records.html', order=order)
    return render_template('lab/recordset_detail.html', customer=customer, order=order)


@lab.route('/orders/<int:order_id>/invoice-items')
@login_required
def show_invoice_items(order_id):
    order = LabTestOrder.query.get(order_id)
    return render_template('lab/partials/invoice_items.html', order=order)


@lab.route('/orders/<int:order_id>/records/<int:record_id>', methods=['POST', 'GET'])
@login_required
def finish_test_record(order_id, record_id):
    order = LabTestOrder.query.get(order_id)
    rec = LabTestRecord.query.get(record_id)
    if not order or not rec:
        flash('The order or the test record no longer exists.', 'danger')
        return redirect(request.referrer)

    LabTestRecordForm = create_lab_test_record_form(rec.test, default=rec.text_result)
    form = LabTestRecordForm(obj=rec)

    if request.method == 'POST':
        if form.validate_on_submit():
            form.populate_obj(rec)
            rec.updated_at = arrow.now('Asia/Bangkok').datetime
            rec.updater = current_user
            if form.choice_set.data:
                rec.text_result = form.choice_set.data.result
            # activity = LabActivity(
            #     lab_id=order.lab_id,
            #     actor=current_user,
            #     message='Added the result for a test record.',
            #     detail=rec.id,
            #     added_at=arrow.now('Asia/Bangkok').datetime
            # )
            order.finished_at = arrow.now('Asia/Bangkok').datetime
            db.session.add(rec)
            # db.session.add(activity)
            db.session.commit()
            flash('New result record has been saved.', 'success')
            return redirect(url_for('lab.show_customer_test_records', order_id=order_id, customer_id=order.customer.id))
        else:
            flash(form.errors, 'danger')
    return render_template('lab/new_test_record.html', form=form, order=order, rec=rec)


@lab.route('/orders/<int:order_id>/approve', methods=['GET', 'PATCH'])
@login_required
def approve_test_order(order_id):
    order = LabTestOrder.query.get(order_id)
    if request.method == 'PATCH':
        if order.approved_at:
            order.approved_at = None
            order.approver = None
            # activity = LabActivity(
            #     lab_id=order.lab_id,
            #     actor=current_user,
            #     message='Cancelled the approval for an order',
            #     detail=order.id,
            #     added_at=arrow.now('Asia/Bangkok').datetime
            # )
            # db.session.add(activity)
    else:
        order.approved_at = arrow.now('Asia/Bangkok').datetime
        order.approver = current_user
    db.session.add(order)
    db.session.commit()
    resp = make_response()
    resp.headers['HX-Refresh'] = 'true'
    # flash('The order approval has been updated.', 'success')
    return resp


@lab.route('/labs/<int:lab_id>/rejects')
@login_required
def list_rejected_orders(lab_id):
    lab = Laboratory.query.get(lab_id)
    records = []
    for order in lab.test_orders:
        for record in order.test_records:
            if record.reject_record:
                records.append(record)
    return render_template('lab/reject_records.html', records=records, lab=lab)


@lab.route('/records/<int:record_id>/revisions')
@login_required
def test_record_revisions(record_id):
    record = LabTestRecord.query.get(record_id)
    return render_template('lab/test_revisions.html', record=record)


@lab.route('/labs/<int:lab_id>/data-export', methods=['GET'])
@login_required
def export_data(lab_id):
    table = request.args.get('table')
    models = {
        'members': UserLabAffil,
        'customers': LabCustomer,
        'activities': LabActivity,
        'tests': LabTest,
        'orders': LabTestOrder,
        'reject_records': LabOrderRejectRecord,
    }
    if table:
        if table == 'results':
            data = []
            lab = Laboratory.query.get(lab_id)
            for order in lab.test_orders:
                for rec in order.test_records:
                    data.append(rec.to_dict())
            df = pd.DataFrame(data)
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False)
            writer.close()
            output.seek(0)
            return send_file(output, download_name=f'{table}.xlsx')
        else:
            model = models[table]
            if table == 'reject_records':
                data = [row.to_dict() for row in model.query]
            else:
                data = [row.to_dict() for row in model.query.filter_by(lab_id=lab_id)]
            df = pd.DataFrame(data)
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False)
            writer.close()
            output.seek(0)
            return send_file(output, download_name=f'{table}.xlsx')

    return render_template('lab/data_export.html', lab_id=lab_id)


@lab.route('/payments/<int:order_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_payment_record(order_id):
    order = LabTestOrder.query.get(order_id)
    record = order.payment
    form = LabPaymentRecordForm(obj=record) if record else LabPaymentRecordForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            if order.payment:
                record = order.payment
                print("Load Payment Record")

            else:
                record = LabOrderPaymentRecord()
                print("Enter Payment Record")

            form.populate_obj(record)

            record.created_at = arrow.now('Asia/Bangkok').datetime
            record.payment_datetime = arrow.now('Asia/Bangkok').datetime
            record.creator = current_user
            record.order = order


            # items = []
            # # for item in order.test_records:
            # #     items.append({
            # #         "type": 1,
            # #         "productCode": item.test.code,
            # #         "name": item.test.name,
            # #         "description": "",
            # #         "quantity": 1,
            # #         "unitName": "Unit",
            # #         "pricePerUnit": str(item.test.price),
            # #         "total": str(item.test.price)
            # #     })
            # for item in order.invoice_items:
            #     items.append(item)

            discountPercentage: int = 0
            discountAmount : float = 0.0

            if record.discount_type == 1:
                discountPercentage = record.discount_amount
                discountAmount = (order.amount_balance - record.grand_total_amount)
            elif record.discount_type == 3:
                discountAmount = record.discount_amount
            else:
                discountAmount = 0.0
                discountPercentage = 0


            invoice = {
                "contactCode": record.order.customer.hn,
                "contactName": record.order.customer.fullname,
                "contactAddress": record.order.customer.address,
                "contactBranch": "000",
                "contactPerson": "",
                "contactEmail": "",
                "contactNumber": record.order.customer.tel,
                "contactTaxId": record.order.customer.pid,
                "creditType": 3,
                "publishedOn": arrow.now('Asia/Bangkok').format('YYYY-MM-DD'),
                "creditDays": 0,
                "dueDate": arrow.now('Asia/Bangkok').format('YYYY-MM-DD'),
                "projectName": "One lab",
                "reference": "Cash",
                "isVatInclusive": False,
                "discountType": record.discount_type,
                "discountPercentage": str(discountPercentage),
                "discountAmount": str(discountAmount),
                "salesName": record.creator.firstname,
                "items": order.invoice_items,
                "subTotal": str(order.amount_balance),
                "totalAfterDiscount": str(record.grand_total_amount),
                "grandTotal": str(record.payment_amount),
                "totalWithoutVat": 0,
                "vatAmount": 0,
                "remarks": request.form.get('payment_remarks'),
                "internalNotes": "ชำระเงินแล้ว",
                "paymentMethod": 1,
                "paymentDate": arrow.now('Asia/Bangkok').format('YYYY-MM-DD'),
                "paymentRemarks": request.form.get('payment_method'),
                "collected": request.form.get('payment_amount'),
                "withheldAmount": 0,
                "withheldPercent": 0,
                "fee": 0
            }

            # print('data', invoice)
            access_token = f"Bearer {get_access_token()}"

            access_url = f"{configuration.host}/cash-invoices/with-payment"
            headers = {
                "Authorization": f"{access_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(access_url, headers=headers, data=json.dumps(invoice))

            document_id = 0

            if response.status_code == 200:
                api_response = response.json()
                print({"success": True, "data": api_response})
                document_id = api_response['data']['documentId']
                receipt_no = api_response['data']['documentSerial']


            else:
                print({"success": False, "error": response.text}, response.status_code)

            record.receipt_id = document_id
            db.session.add(record)
            db.session.commit()

            flash('Payment record has been saved.', 'success')
        else:
            flash(f'An error occurred. {form.errors}', 'danger')

        resp = make_response()
        resp.headers['HX-Refresh'] = 'true'
        return resp
    return render_template('lab/modals/payment_form.html', form=form, order=order)




@lab.route('/receipt/<int:order_id>/preview', methods=['GET', 'POST'])
@login_required
def receipt_view(order_id):
    order = LabTestOrder.query.get(order_id)
    record = order.payment


    document = {
         "documentId" : record.receipt_id
    }

    access_token = f"Bearer {get_access_token()}"

    access_url = f"{configuration.host}/cash-invoices/sharedocument"
    headers = {
        "Authorization": f"{access_token}",
        "Content-Type": "application/json"
    }


    response = requests.post(access_url, headers=headers, data=json.dumps(document))


    if response.status_code == 200:
        api_response = response.json()
        link = api_response['data']['link']
        return jsonify({"success": True, "link": link})
    else:
        return jsonify({"success": False, "error": response.text}), response.status_code



@lab.route('/reports/<int:order_id>/preview', methods=['GET', 'POST'])
@login_required
def preview_report(order_id):
    order = LabTestOrder.query.get(order_id)
    return render_template('lab/lab_report_preview.html', order=order)


@lab.route('/reports/<int:order_id>/print', methods=['GET', 'POST'])
@login_required
def print_report(order_id):
    order = LabTestOrder.query.get(order_id)
    return render_template('lab/lab_report_print.html', order=order)


@lab.route('/requests/<int:order_id>/preview', methods=['GET', 'POST'])
@login_required
def preview_request(order_id):
    order = LabTestOrder.query.get(order_id)
    return render_template('lab/lab_request_preview.html', order=order)


sarabun_font = TTFont('Sarabun', 'app/static/fonts/THSarabunNew.ttf')
pdfmetrics.registerFont(sarabun_font)
style_sheet = getSampleStyleSheet()
style_sheet.add(ParagraphStyle(name='ThaiStyle', fontName='Sarabun'))
style_sheet.add(ParagraphStyle(name='ThaiStyleNumber', fontName='Sarabun', alignment=TA_RIGHT))
style_sheet.add(ParagraphStyle(name='ThaiStyleCenter', fontName='Sarabun', alignment=TA_CENTER))
style_sheet.add(ParagraphStyle(name='ThaiStyleRight', fontName='Sarabun', alignment=TA_RIGHT))

bangkok = pytz.timezone('Asia/Bangkok')


def generate_receipt_pdf(order, sign=False, cancel=False):
    logo = Image('app/static/img/ONELAB-01-mini.png', width=200)

    this_lab = Laboratory.query.get(session.get('lab_id'))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer,
                            rightMargin=20,
                            leftMargin=20,
                            topMargin=180,
                            bottomMargin=10,
                            )
    receipt_number = order.code
    data = []
    affiliation = f'''<para align=center><font size=28>
            {this_lab.name}
            </font></para>
            '''
    address = f'''<br/><br/><br/><br/><font size=10>
            ที่อยู่ / Address <br/>
            {this_lab.address}<br/><br/>
            เลขประจำตัวผู้เสียภาษี / TAX ID<br/>
            {this_lab.tax_id}
            </font>
            '''

    receipt_info = '''<br/><br/><br/><br/><font size=10>
            เลขที่ / NO. {receipt_number}<br/>
            วันที่ / DATE {issued_date}<br/>
            ออกโดย / ISSUER {issuer}<br/><br/>
            พิมพ์เมื่อ / PRINT TIME {issue_datetime}<br/>
            </font>
            '''
    issued_date = arrow.get(order.payment.created_at.astimezone(bangkok)).format(fmt='DD MMMM YYYY HH:mm:ss',
                                                                                 locale='th-th')
    receipt_info_ori = receipt_info.format(receipt_number=receipt_number,
                                           issued_date=issued_date,
                                           issuer=current_user,
                                           issue_datetime=datetime.now().astimezone(bangkok).strftime(
                                               '%d/%m/%Y %H:%M:%S')
                                           )

    header_content_ori = [[Paragraph(address, style=style_sheet['ThaiStyle']),
                           [logo],
                           Paragraph(receipt_info_ori, style=style_sheet['ThaiStyle'])]]

    header_styles = TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ])

    header_ori = Table(header_content_ori, colWidths=[130, 240, 150])

    header_ori.hAlign = 'CENTER'
    header_ori.setStyle(header_styles)

    customer_name = '''<para><font size=11>
    ได้รับเงินจาก / PAYER {issued_for}<br/>
    ที่อยู่ / ADDRESS<br/>{address}
    </font></para>
    '''.format(issued_for=order.customer.fullname,
               address='<br/>'.join(textwrap.wrap(order.customer.address, width=100)))
    customer = Paragraph(customer_name, style=style_sheet['ThaiStyle'])
    items = [[Paragraph('<font size=14>ลำดับ / No.</font>', style=style_sheet['ThaiStyleCenter']),
              Paragraph('<font size=14>รายการ / Description</font>', style=style_sheet['ThaiStyleCenter']),
              Paragraph('<font size=14>รวม / Total</font>', style=style_sheet['ThaiStyleCenter']),
              ]]
    total = 0
    number_test = 0
    total_profile_price = 0
    total_special_price = 0
    # if receipt.print_profile_note:
    #     profile_tests = [t for t in receipt.record.ordered_tests if t.profile]
    #     if profile_tests:
    #         if receipt.print_profile_how == 'consolidated':
    #             number_test += 1
    #             profile_price = profile_tests[0].profile.quote
    #             if profile_price > 0:
    #                 item = [
    #                     Paragraph('<font size=12>{}</font>'.format(number_test), style=style_sheet['ThaiStyleCenter']),
    #                     Paragraph('<font size=12>การตรวจสุขภาพทางห้องปฏิบัติการ / Laboratory Tests</font>',
    #                               style=style_sheet['ThaiStyle']),
    #                     Paragraph('<font size=12>{:,.2f}</font>'.format(profile_price),
    #                               style=style_sheet['ThaiStyleNumber']),
    #                     Paragraph('<font size=12>-</font>', style=style_sheet['ThaiStyleCenter']),
    #                     Paragraph('<font size=12>{:,.2f}</font>'.format(profile_price),
    #                               style=style_sheet['ThaiStyleNumber']),
    #                     ]
    #                 items.append(item)
    #                 total_profile_price += profile_price
    #                 total += profile_price
    #             else:
    #                 for t in receipt.record.ordered_tests:
    #                     if t.profile:
    #                         total_profile_price += t.price
    #                         total += t.price
    #                 item = [Paragraph('<font size=12>{}</font>'.format(number_test),
    #                                   style=style_sheet['ThaiStyleCenter']),
    #                         Paragraph('<font size=12>การตรวจสุขภาพทางห้องปฏิบัติการ / Laboratory Tests</font>',
    #                                   style=style_sheet['ThaiStyle']),
    #                         Paragraph('<font size=12>{:,.2f}</font>'.format(total_profile_price),
    #                                   style=style_sheet['ThaiStyleNumber']),
    #                         Paragraph('<font size=12>-</font>', style=style_sheet['ThaiStyleCenter']),
    #                         Paragraph('<font size=12>{:,.2f}</font>'.format(total_profile_price),
    #                                   style=style_sheet['ThaiStyleNumber']),
    #                         ]
    #                 items.append(item)
    for t in order.active_test_records:
        price = t.test.price
        total += price
        number_test += 1
        item = [Paragraph('<font size=14>{}</font>'.format(number_test), style=style_sheet['ThaiStyleCenter']),
                Paragraph('<font size=14>{} ({})</font>'
                          .format(t.test.name, t.test.detail or '-'),
                          style=style_sheet['ThaiStyle']),
                Paragraph('<font size=14>{:,.2f}</font>'.format(price), style=style_sheet['ThaiStyleNumber'])]
        items.append(item)

    total_thai = bahttext(total)
    total_text = "รวมเงินทั้งสิ้น {}".format(total_thai)
    items.append([
        Paragraph('<font size=14></font>', style=style_sheet['ThaiStyle']),
        Paragraph('<font size=14></font>', style=style_sheet['ThaiStyle']),
        Paragraph('<font size=14></font>', style=style_sheet['ThaiStyle']),
    ])
    items.append([
        Paragraph('<font size=14>{}</font>'.format(total_text), style=style_sheet['ThaiStyle']),
        Paragraph('<font size=14></font>', style=style_sheet['ThaiStyle']),
        Paragraph('<font size=14>{:,.2f}</font>'.format(total), style=style_sheet['ThaiStyleNumber'])
    ])
    item_table = Table(items, colWidths=[50, 350, 70], repeatRows=1, cornerRadii=(5, 5, 5, 5))
    item_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, 0), 0.25, colors.black),
        ('BOX', (0, -1), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (0, -1), 0.25, colors.black),
        ('BOX', (1, 0), (1, -1), 0.25, colors.black),
        ('BOX', (2, 0), (2, -1), 0.25, colors.black),
        # ('BOX', (0, 0), (2, 32), 0.25, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, -2), (-1, -2), 10),
    ]))
    item_table.setStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')])
    item_table.setStyle([('SPAN', (0, -1), (1, -1))])

    if order.payment.payment_method == 'Cash':
        payment_info = Paragraph('<font size=14>ชำระเงินด้วย / PAYMENT METHOD: เงินสด / CASH</font>',
                                 style=style_sheet['ThaiStyleRight'])
    elif order.payment.payment_method == 'QR':
        payment_info = Paragraph('<font size=14>ชำระเงินด้วย / PAYMENT METHOD: QR / QR</font>',
                                 style=style_sheet['ThaiStyleRight'])
    elif order.payment.payment_method == 'Credit Card':
        payment_info = Paragraph(
            '<font size=14>ชำระเงินด้วย / PAYMENT METHOD บัตรเครดิต / CREDIT CARD: หมายเลข / NUMBER {}-****-****-{}</font>'.format(
                order.payment.card_number[:4], order.payment.card_number[-4:]),
            style=style_sheet['ThaiStyleRight'])
    else:
        payment_info = Paragraph('<font size=14>ยังไม่ชำระเงิน / UNPAID</font>', style=style_sheet['ThaiStyleRight'])

    sign_text = Paragraph(
        '<br/><br/><br/><br/><font size=14>...................................<br/>({})<br/><br/>ผู้รับเงิน / CASHIER<br/></font>'.format(
            order.payment.creator.fullname),
        style=style_sheet['ThaiStyleCenter'])
    total_content = [
        [
            payment_info,
        ],
        [
            Paragraph(
                f"<font size=14>เมื่อ / Date Time {order.payment.payment_datetime.strftime('%d/%m/%Y %H:%M:%S')}</font>",
                style=style_sheet['ThaiStyleRight']),
        ],
        [
            sign_text
        ]
    ]

    total_table = Table(total_content, colWidths=[400])

    def first_page_setup(canvas, doc):
        canvas.saveState()
        # Head
        header = header_ori
        w, h = header.wrap(doc.width, doc.topMargin)
        header.drawOn(canvas, doc.leftMargin + 28, doc.height + doc.topMargin - h)

        subheader1 = Paragraph('<para align=center><font size=16>ใบเสร็จรับเงิน / RECEIPT<br/><br/></font></para>',
                               style=style_sheet['ThaiStyle'])
        w, h = subheader1.wrap(doc.width, doc.topMargin)
        subheader1.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h * 5.5)

        subheader2 = customer
        w, h = subheader2.wrap(doc.width, doc.topMargin)
        subheader2.drawOn(canvas, doc.leftMargin + 48, doc.height + doc.topMargin - h * 4.5)

        # logo_image = ImageReader('app/static/img/mu-watermark.png')
        # canvas.drawImage(logo_image, 140, 265, mask='auto')
        canvas.restoreState()

    def later_pages_setup(canvas, doc):
        canvas.saveState()
        header = header_ori
        w, h = header.wrap(doc.width, doc.topMargin)
        header.drawOn(canvas, doc.leftMargin + 28, doc.height + doc.topMargin - h)

        subheader1 = Paragraph('<para align=center><font size=16>ใบเสร็จรับเงิน / RECEIPT<br/><br/></font></para>',
                               style=style_sheet['ThaiStyle'])
        w, h = subheader1.wrap(doc.width, doc.topMargin)
        subheader1.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h * 5.5)

        subheader2 = customer
        w, h = subheader2.wrap(doc.width, doc.topMargin)
        subheader2.drawOn(canvas, doc.leftMargin + 48, doc.height + doc.topMargin - h * 4.5)
        # logo_image = ImageReader('app/static/img/mu-watermark.png')
        # canvas.drawImage(logo_image, 140, 265, mask='auto')
        canvas.restoreState()

    data.append(KeepTogether(item_table))
    data.append(KeepTogether(Spacer(1, 12)))
    data.append(KeepTogether(total_table))

    doc.build(data, onFirstPage=first_page_setup, onLaterPages=later_pages_setup, canvasmaker=PageNumCanvas)
    buffer.seek(0)
    return buffer


class PageNumCanvas(canvas.Canvas):
    """
    http://code.activestate.com/recipes/546511-page-x-of-y-with-reportlab/
    http://code.activestate.com/recipes/576832/
    """

    # ----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """Constructor"""
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    # ----------------------------------------------------------------------
    def showPage(self):
        """
        On a page break, add information to the list
        """
        self.pages.append(dict(self.__dict__))
        self._startPage()

    # ----------------------------------------------------------------------
    def save(self):
        """
        Add the page number to each page (page x of y)
        """
        page_count = len(self.pages)

        for page in self.pages:
            self.__dict__.update(page)
            self.draw_page_number(page_count)
            canvas.Canvas.showPage(self)

        canvas.Canvas.save(self)

    # ----------------------------------------------------------------------
    def draw_page_number(self, page_count):
        """
        Add the page number
        """
        page = "%s/%s" % (self._pageNumber, page_count)
        self.setFont("Sarabun", 12)
        self.drawRightString(195 * mm, 290 * mm, page)


@lab.route('/orders/<int:order_id>/payment-export')
@login_required
def export_receipt_pdf(order_id):
    order = LabTestOrder.query.get(order_id)
    receipt = generate_receipt_pdf(order)
    return send_file(receipt, mimetype='application/pdf')


@lab.route('/labs/<int:lab_id>/geo-checkin', methods=['GET', 'POST'])
@login_required
def geo_checkin(lab_id):
    lab = Laboratory.query.get(lab_id)
    affil = UserLabAffil.query.filter_by(lab_id=lab_id, user=current_user).first()
    if request.method == 'POST':
        if affil:
            session['lab_id'] = lab_id
            req_data = request.get_json()
            place = req_data['data'].get('place', '0.0')
            lat = req_data['data'].get('lat', '0.0')
            lon = req_data['data'].get('lon', '0.0')
            now = datetime.now(pytz.utc)
            tz = pytz.timezone('Asia/Bangkok')
            date_id = UserCheckinRecord.generate_date_id(now.astimezone(tz))

            if place == 'gj':
                record = UserCheckinRecord(
                    date_id=date_id,
                    usesr=current_user,
                    lat=float(lat),
                    long=float(lon),
                    start_datetime=now,
                )
                activity = ''
            else:
                # use the first login of the day as the checkin time.
                # use the last login of the day as the checkout time.
                record = UserCheckinRecord.query.filter_by(date_id=date_id, user=current_user).first()

                if not record:
                    record = UserCheckinRecord(
                        date_id=date_id,
                        user=current_user,
                        lat=float(lat),
                        long=float(lon),
                        start_datetime=now,
                    )
                    activity = 'checked in'
                else:
                    record.end_datetime = now
                    activity = 'checked out'
            db.session.add(record)
            db.session.commit()
            return jsonify({'message': 'success',
                            'activity': activity,
                            'name': current_user.fullname,
                            'time': now.isoformat(),
                            })
    return render_template('lab/geo_checkin.html', lab=lab)


@lab.route('/labs/<int:lab_id>/test-profiles', methods=['GET', 'POST'])
@login_required
def test_profiles(lab_id):
    profiles = LabTestProfile.query.filter_by(lab_id=lab_id, active=True)
    return render_template('lab/test_profiles.html', test_profiles=profiles, lab_id=lab_id)


@lab.route('/labs/<int:lab_id>/add-test-profile', methods=['GET', 'POST'])
@lab.route('/labs/<int:lab_id>/profiles/<int:profile_id>', methods=['GET', 'POST'])
@login_required
def add_test_profile(lab_id, profile_id=None):
    TestProfileForm = create_lab_test_profile_form(lab_id)
    if not profile_id:
        form = TestProfileForm()
    else:
        profile = LabTestProfile.query.get(profile_id)
        form = TestProfileForm(obj=profile)
    if form.validate_on_submit():
        if not form.test_order.data:
            form.test_order.data = ','.join([t.code for t in form.tests.data])
        if not profile_id:
            profile = LabTestProfile(lab_id=lab_id)

        if profile:
            form.populate_obj(profile)
            try:
                db.session.add(profile)
                db.session.commit()
            except db.exc.IntegrityError as e:
                db.session.rollback()
                flash('The profile code already exists.', 'danger')
            else:
                if profile_id:
                    flash('The test profile has been updated.', 'success')
                else:
                    flash('New test profile has been added.', 'success')
                return redirect(url_for('lab.test_profiles', lab_id=lab_id))

    return render_template('lab/test_profile_form.html', form=form, lab_id=lab_id)


@lab.route('/orders/<int:order_id>/profiles/<int:profile_id>/test-records', methods=['GET', 'POST'])
@login_required
def edit_test_profile_record(order_id, profile_id):
    order = LabTestOrder.query.get(order_id)
    profile = LabTestProfile.query.get(profile_id)
    LabTestProfileRecordForm = create_lab_test_profile_record_form(profile.test_order)
    code_names = profile.test_order.split(',')
    form = LabTestProfileRecordForm()
    if request.method == 'GET':
        for field in form:
            if field.name not in code_names:
                continue
            test = LabTest.query.filter_by(code=field.name).first()
            _record = LabTestRecord.query.filter_by(test_id=test.id,
                                                    order_id=order_id,
                                                    profile_id=profile_id).first()
            if _record:
                if _record.test.choice_set:
                    for c in _record.test.choice_set.choice_items:
                        if c.result == _record.text_result:
                            field.choice_set.data = c
                    field.text_result.data = ""
                else:
                    field.text_result.data = _record.text_result
                field.num_result.data = _record.num_result
                field.comment.data = _record.comment

    if form.validate_on_submit():
        for field in form:
            if field.name not in code_names:
                continue
            test = LabTest.query.filter_by(code=field.name).first()
            _record = LabTestRecord.query.filter_by(test_id=test.id,
                                                    order_id=order_id,
                                                    profile_id=profile_id).first()
            if not _record:
                _record = LabTestRecord(order=order_id, profile_id=profile_id, test_id=test.id)

            print(field.name, field.numeric.data)

            if field.numeric.data:
                _record.num_result = field.num_result.data
            else:
                if field.choice_set.data:
                    _record.text_result = field.choice_set.data.result
                else:
                    _record.text_result = field.text_result.data
            _record.comment = field.comment.data
            _record.updated_at = arrow.now('Asia/Bangkok').datetime
            _record.updater = current_user
            db.session.add(_record)
        db.session.commit()
        flash("Results have been saved.", "success")
        return redirect(url_for('lab.show_customer_test_records', order_id=order_id))
    return render_template('lab/test_profile_record_form.html',
                           form=form, order=order, profile=profile, code_names=code_names)


@lab.route('/lab/<int:lab_id>/packages', methods=['GET', 'POST'])
@login_required
def list_service_packages(lab_id):
    lab = Laboratory.query.get(lab_id)
    return render_template('lab/service_package_list.html', lab=lab)


@lab.route('/lab/<int:lab_id>/package-form', methods=['GET', 'POST'])
@lab.route('/lab/<int:lab_id>/packages/<int:package_id>', methods=['GET', 'POST'])
@login_required
def edit_service_package(lab_id=None, package_id=None):
    if package_id:
        package = LabServicePackage.query.get(package_id)
        form = LabServicePackageForm(obj=package)
    else:
        form = LabServicePackageForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            if not package_id:
                package = LabServicePackage(lab_id=lab_id)

            form.populate_obj(package)
            package.creator = current_user
            package.created_at = arrow.now('Asia/Bangkok').datetime
            try:
                db.session.add(package)
                db.session.commit()
            except db.exc.IntegrityError as e:
                db.session.rollback()
                flash('The package code already exists.', 'danger')
            else:
                if package_id:
                    flash('The package has been updated.', 'success')
                else:
                    flash('The new package has been added.', 'success')
                return redirect(url_for('lab.list_service_packages', lab_id=lab_id))
        else:
            flash(form.errors, 'danger')
    return render_template('lab/service_package_form.html', form=form, lab_id=lab_id)


@lab.route('/packages/<int:package_id>/items', methods=['GET', 'POST'])
@login_required
def manage_service_package_items(package_id):
    package = LabServicePackage.query.get(package_id)
    return render_template('lab/service_package_items.html', package=package)


@lab.route('/packages/<int:package_id>/tests', methods=['GET', 'POST'])
@login_required
def edit_tests_service_package(package_id=None):
    package = LabServicePackage.query.get(package_id)
    LabServicePackageTestsForm = create_lab_service_package_tests_form(package.lab_id)
    form = LabServicePackageTestsForm(obj=package)
    if request.method == 'POST':
        if form.validate_on_submit():
            form.populate_obj(package)
            package.updated_at = arrow.now('Asia/Bangkok').datetime
            db.session.add(package)
            db.session.commit()
            flash('The package has been updated.', 'success')
            resp = make_response()
            resp.headers['HX-Refresh'] = 'true'
            return resp
        else:
            print(form.errors)
            resp = make_response()
            resp.headers['HX-Trigger'] = 'closeModal'
            return resp
    return render_template('lab/modals/service_package_tests_form.html', form=form, package=package)


@lab.route('/packages/<int:package_id>/profiles', methods=['GET', 'POST'])
@login_required
def edit_profiles_service_package(package_id=None):
    package = LabServicePackage.query.get(package_id)
    LabServicePackageProfilesForm = create_lab_service_package_profiles_form(package.lab_id)
    form = LabServicePackageProfilesForm(obj=package)
    if request.method == 'POST':
        if form.validate_on_submit():
            form.populate_obj(package)
            package.updated_at = arrow.now('Asia/Bangkok').datetime
            db.session.add(package)
            db.session.commit()
            flash('The package has been updated.', 'success')
            resp = make_response()
            resp.headers['HX-Refresh'] = 'true'
            return resp
        else:
            print(form.errors)
            resp = make_response()
            resp.headers['HX-Trigger'] = 'closeModal'
            return resp
    return render_template('lab/modals/service_package_profiles_form.html', form=form, package=package)


@lab.route('/api/customers/search')
def search_customers():
    query = request.args.get('query')
    customers = []
    if query:
        try:
            firstname, lastname = query.split(' ')
        except ValueError:
            customers += LabCustomer.query.filter(or_(
                LabCustomer.firstname.like(f"%{query}%"),
                LabCustomer.lastname.like(f"%{query}%"),
                LabCustomer.hn.like(f"%{query}"),
            )).all()
        else:
            customers += LabCustomer.query.filter(and_(
                LabCustomer.firstname.like(f'%{firstname}%'),
                LabCustomer.lastname.like(f'%{lastname}%')
            )).all()
    template = ''
    for customer in customers:
        url = url_for('lab.show_customer_records', customer_id=customer.id)
        template += f'<tr><td>{customer.hn}</td><td>{customer.firstname} {customer.lastname}</td><td><a href="{url}" class="button is-rounded is-info"><span class="icon"><i class="fas fa-info-circle"></i></span><span>Info</span></a></td>'

    return template


@lab.route('/api/packages/<int:package_id>/info')
def show_package_info(package_id: int):
    package = LabServicePackage.query.get(package_id)
    return render_template('lab/modals/package_info.html', package=package)
