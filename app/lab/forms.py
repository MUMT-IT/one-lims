from flask import session
from flask_wtf import FlaskForm, Form
from wtforms import BooleanField, StringField, TextField, DecimalField, SelectField
from wtforms.fields import BooleanField
from wtforms import FormField, FieldList
from wtforms.widgets import Select
from wtforms.validators import InputRequired, Optional
from wtforms.widgets.core import CheckboxInput, ListWidget
from wtforms_alchemy import model_form_factory, QuerySelectField
from wtforms_alchemy.fields import QuerySelectField, QuerySelectMultipleField, ModelFormField, ModelFieldList

from .models import *
from app import db

BaseModelForm = model_form_factory(FlaskForm)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(self):
        return db.session


class ChoiceSetForm(FlaskForm):
    name = StringField('Name', validators=[
        InputRequired()
    ])
    reference = StringField('Reference')


class ChoiceItemForm(FlaskForm):
    result = StringField('Result', validators=[
        InputRequired()
    ])
    interpretation = StringField('Interpretation', validators=[
        InputRequired()
    ])
    ref = BooleanField('Is this a reference value?')


def create_lab_specimen_container_item_form(lab_id):
    class LabSpecimenContainerItemForm(ModelForm):
        class Meta:
            model = LabSpecimenContainerItem

        specimen_container = QuerySelectField('Container',
                                              allow_blank=True,
                                              blank_text='Select container',
                                              query_factory=lambda: LabSpecimenContainer.query.filter_by(lab_id=lab_id))

    return LabSpecimenContainerItemForm


def create_lab_test_form(lab_id):
    LabSpecimenContainerItemForm = create_lab_specimen_container_item_form(lab_id)

    class LabTestForm(ModelForm):
        class Meta:
            model = LabTest

        choice_set = QuerySelectField('Choice Set',
                                      widget=Select(),
                                      allow_blank=True,
                                      blank_text='ไม่ใช้ชุดคำตอบ',
                                      validators=[Optional()]
                                      )
        specimen_container_items = ModelFieldList(
            ModelFormField(LabSpecimenContainerItemForm, default=LabSpecimenContainerItem()),
            min_entries=2)
    return LabTestForm


def create_customer_form(lab_id):
    class LabCustomerForm(ModelForm):
        class Meta:
            model = LabCustomer
            exclude = ['hn']

    return LabCustomerForm


def create_lab_test_record_form(test, default=None):
    default_choice = LabResultChoiceItem.query.filter_by(choice_set_id=test.choice_set_id, result=default).first()
    if default_choice:
        default_choice = lambda: LabResultChoiceItem.query.filter_by(choice_set_id=test.choice_set_id,
                                                                     result=default).first()

    class LabTestRecordForm(ModelForm):
        class Meta:
            model = LabTestRecord

        choice_set = QuerySelectField('Result choices',
                                      query_factory=lambda: [] if not test.choice_set else test.choice_set.choice_items,
                                      allow_blank=True,
                                      blank_text='Please select',
                                      default=default_choice,
                                      validators=[Optional()])
        numeric = BooleanField('Numeric Result', default=True if test.data_type == "Numeric" else False)

    return LabTestRecordForm


def create_lab_test_profile_record_form(order):
    class LabTestProfileRecordForm(FlaskForm):
        code_list = order.split(',')
        field_list = []
        for code in code_list:
            test = LabTest.query.filter_by(code=code).first()
            form = create_lab_test_record_form(test)
            vars()[code] = FormField(form, default=LabTestRecord)
    return LabTestProfileRecordForm


class LabOrderRejectRecordForm(ModelForm):
    class Meta:
        model = LabOrderRejectRecord
        field_args = {'created_at': {'validators': [Optional()]}}


class LabForm(ModelForm):
    class Meta:
        model = Laboratory


class LabPhysicalExamRecordForm(ModelForm):
    class Meta:
        model = LabPhysicalExamRecord
        exclude = ['created_at']


class LabPaymentRecordForm(ModelForm):
    class Meta:
        model = LabOrderPaymentRecord
        exclude = ['created_at', 'expired_at', 'payment_datetime']


def create_lab_test_profile_form(lab_id):
    class LabTestProfileForm(ModelForm):
        class Meta:
            model = LabTestProfile

        tests = QuerySelectMultipleField('Tests',
                                         query_factory=lambda: LabTest.query.filter_by(lab_id=lab_id),
                                         widget=ListWidget(prefix_label=False),
                                         option_widget=CheckboxInput()
                                         )
    return LabTestProfileForm


class LabServicePackageForm(ModelForm):
    class Meta:
        model = LabServicePackage
        exclude = ['created_at']


def create_lab_service_package_tests_form(lab_id):
    class LabServicePackageTestsForm(ModelForm):
        class Meta:
            model = LabServicePackage
            exclude = ['name', 'created_at']
        tests = QuerySelectMultipleField('Tests',
                                         query_factory=lambda: LabTest.query.filter_by(lab_id=lab_id),
                                         widget=ListWidget(prefix_label=False),
                                         option_widget=CheckboxInput())

    return LabServicePackageTestsForm


def create_lab_service_package_profiles_form(lab_id):
    class LabServicePackageProfilesForm(ModelForm):
        class Meta:
            model = LabServicePackage
            exclude = ['created_at', 'name']

        profiles = QuerySelectMultipleField('Profiles',
                                            query_factory=lambda: LabTestProfile.query.filter_by(lab_id=lab_id),
                                            widget=ListWidget(prefix_label=False),
                                            option_widget=CheckboxInput())

    return LabServicePackageProfilesForm
