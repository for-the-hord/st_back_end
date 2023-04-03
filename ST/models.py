# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class File(models.Model):
    id = models.TextField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    path = models.TextField(blank=True, null=True)
    create_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'file'


class Template(models.Model):
    id = models.TextField(primary_key=True)
    unit_id = models.TextField(blank=True, null=True)
    template = models.TextField(blank=True, null=True)
    user_id = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    file_id = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'template'


class TpData(models.Model):
    id = models.TextField(primary_key=True)
    tp_id = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    data = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tp_data'


class Unit(models.Model):
    id = models.TextField(primary_key=True)
    name = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'unit'


class User(models.Model):
    id = models.TextField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    password = models.TextField(blank=True, null=True)
    unit_id = models.TextField(blank=True, null=True)
    account = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user'
