from flask import session
from flask_wtf import FlaskForm, Form
from wtforms import BooleanField, StringField, TextField, DecimalField, SelectField
from wtforms.fields import BooleanField
from wtforms.fields.core import FormField, FieldList
from wtforms.widgets import Select
from wtforms.validators import InputRequired, Optional
from wtforms_alchemy import model_form_factory, QuerySelectField
from wtforms_alchemy.fields import QuerySelectField

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


class LabSpecimenContainerItemForm(ModelForm):
    class Meta:
        model = LabSpecimenContainerItem

    specimen_container = QuerySelectField('Container',
                                          allow_blank=True,
                                          blank_text='Select container',
                                          query_factory=lambda: LabSpecimenContainer.query.filter_by(lab_id=session.get('lab_id')))


class LabTestForm(ModelForm):
    class Meta:
        model = LabTest

    choice_set = QuerySelectField('Choice Set',
                                  widget=Select(),
                                  allow_blank=True,
                                  blank_text='ไม่ใช้ชุดคำตอบ',
                                  validators=[Optional()]
                                  )
    container_item = FormField(LabSpecimenContainerItemForm, default=LabSpecimenContainerItem())


class LabCustomerForm(ModelForm):
    class Meta:
        model = LabCustomer


def create_lab_test_record_form(test, default=None):
    default_choice = LabResultChoiceItem.query.filter_by(choice_set_id=test.choice_set_id, result=default).first()
    if default_choice:
        default_choice = lambda: LabResultChoiceItem.query.filter_by(choice_set_id=test.choice_set_id, result=default).first()

    class LabTestRecordForm(ModelForm):
        class Meta:
            model = LabTestRecord

        choice_set = QuerySelectField('Result choices',
                                      query_factory=lambda: [] if not test.choice_set else test.choice_set.choice_items,
                                      allow_blank=False,
                                      default=default_choice,
                                      validators=[Optional()])

    return LabTestRecordForm


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
