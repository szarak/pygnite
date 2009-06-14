#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

from html import *
from validators import *

from sql import SQLStorage, SQLDB
from utils import Storage

import uuid
import urllib
import re
import sys
import os
import shutil
import cStringIO
import copy
import base64

table_field = re.compile('[\w_]+\.[\w_]+')
re_extension = re.compile('\.\w{1,5}$')

class StringWidget:

    @staticmethod
    def widget(field, value):
        if value == None:
            value = ''
        id = '%s_%s' % (field._tablename, field.name)
        return INPUT(
            _type='text',
            _id=id,
            _class=field.type,
            _name=field.name,
            value=str(value),
            requires=field.requires,
            )


class IntegerWidget(StringWidget):

    pass


class DoubleWidget(StringWidget):

    pass


class TimeWidget(StringWidget):

    pass


class DateWidget(StringWidget):

    pass


class DatetimeWidget(StringWidget):

    pass


class TextWidget:

    @staticmethod
    def widget(field, value):
        id = '%s_%s' % (field._tablename, field.name)
        return TEXTAREA(
            _id=id,
            _class=field.type,
            _name=field.name,
            value=value,
            requires=field.requires,
            )


class BooleanWidget:

    @staticmethod
    def widget(field, value):
        id = '%s_%s' % (field._tablename, field.name)
        return INPUT(
            _type='checkbox',
            _id=id,
            _class=field.type,
            _name=field.name,
            value=value,
            requires=field.requires,
            )


class OptionsWidget:

    @staticmethod
    def has_options(field):
        return hasattr(field.requires, 'options')\
             or isinstance(field.requires, IS_NULL_OR)\
             and hasattr(field.requires.other, 'options')

    @staticmethod
    def widget(field, value):
        id = '%s_%s' % (field._tablename, field.name)
        if isinstance(field.requires, IS_NULL_OR)\
             and hasattr(field.requires.other, 'options'):
            opts = [OPTION(_value='')]
            options = field.requires.other.options()
        elif hasattr(field.requires, 'options'):
            opts = []
            options = field.requires.options()
        else:
            raise SyntaxError, 'widget cannot determine options of %s' % field 
        opts += [OPTION(v, _value=k) for (k, v) in options]
        return SELECT(*opts, **dict(_id=id, _class=field.type,
                      _name=field.name, value=value,
                      requires=field.requires))


class MultipleOptionsWidget:

    @staticmethod
    def widget(field, value, size=5):
        id = '%s_%s' % (field._tablename, field.name)
        if isinstance(field.requires, IS_NULL_OR)\
             and hasattr(field.requires.other, 'options'):
            opts = [OPTION(_value='')]
            options = field.requires.other.options()
        elif hasattr(field.requires, 'options'):
            opts = []
            options = field.requires.options()
        else:
            raise SyntaxError, 'widget cannot determine options'
        opts += [OPTION(v, _value=k) for (k, v) in options]
        return SELECT(*opts, **dict(
            _id=id,
            _class=field.type,
            _multiple='multiple',
            value=value,
            _name=field.name,
            requires=field.requires,
            _size=min(size, len(opts)),
            ))


class PasswordWidget:

    @staticmethod
    def widget(field, value):
        id = '%s_%s' % (field._tablename, field.name)
        if value:
            value = '********'
        return INPUT(
            _type='password',
            _id=id,
            _name=field.name,
            _value=value,
            _class=field.type,
            requires=field.requires,
            )


class UploadWidget:

    @staticmethod
    def widget(field, value, download_url=None):
        id = '%s_%s' % (field._tablename, field.name)
        inp = INPUT(_type='file', _id=id, _class=field.type,
                    _name=field.name, requires=field.requires)
        if download_url and value:
            url = download_url + '/' + value
            (br, image) = ('', '')
            if UploadWidget.is_image(value):
                (br, image) = (BR(), IMG(_src=url, _width='150px'))
            inp = DIV(
                inp,
                '[',
                A('file', _href=url),
                '|',
                INPUT(_type='checkbox', _name=field.name + '__delete'),
                'delete]',
                br,
                image,
                )
        return inp

    @staticmethod
    def represent(field, value, download_url=None):
        id = '%s_%s' % (field._tablename, field.name)
        inp = 'file'
        if download_url and value:
            url = download_url + '/' + value
            if UploadWidget.is_image(value):
                return A(IMG(_src=url, _width='150px'), _href=url)
            return A('file', _href=url)
        return inp

    @staticmethod
    def is_image(value):
        extension = value.split('.')[-1].lower()
        if extension in ['gif', 'png', 'jpg', 'jpeg', 'bmp']:
            return True
        return False


class SQLFORM(FORM):

    """
    SQLFORM is used to map a table (and a current record) into an HTML form
   
    given a SQLTable stored in db.table

    SQLFORM(db.table) generates an insert form
    record=db(db.table.id==some_id).select()[0]
    SQLFORM(db.table,record) generates an update form
    SQLFORM(db.table,record,deletable=True) generates an update 
                                            with a delete button
    if record is an int, record=db(db.table.id==record).select()[0]
    optional arguments:
    
    fields: a list of fields that should be placed in the form, default is all.
    labels: a dictionary with labels for each field. keys are field names.
    col3  : a dictionary with content for an optional third column 
            (right of each field). keys are field names.
    linkto: the URL of a controller/function to access referencedby records
            see controller appadmin.py for examples
    upload: the URL of a controller/function to download an uploaded file
            see controller appadmin.py for examples
    any named optional attribute is passed to the <form> tag
            for example _class, _id, _style, _action,_method, etc.

    """

    # usability improvements proposal by fpp - 4 May 2008 :
    # - correct labels (for points to field id, not field name)
    # - add label for delete checkbox
    # - add translatable label for record ID
    # - add third column to right of fields, populated from the col3 dict

    widgets = Storage(dict(
        string=StringWidget,
        text=TextWidget,
        password=PasswordWidget,
        integer=IntegerWidget,
        double=DoubleWidget,
        time=TimeWidget,
        date=DateWidget,
        datetime=DatetimeWidget,
        upload=UploadWidget,
        boolean=BooleanWidget,
        blob=None,
        options=OptionsWidget,
        multiple=MultipleOptionsWidget,
        ))

    def __init__(
        self,
        table,
        record=None,
        deletable=False,
        linkto=None,
        upload=None,
        fields=None,
        labels=None,
        col3={},
        submit_button='Submit',
        delete_label='Check to delete:',
        showid=True,
        readonly=False,
        comments=True,
        keepopts=[],
        ignore_rw=False,
        **attributes
        ):
        """
        SQLFORM(db.table,
               record=None,
               fields=['name'],
               labels={'name':'Your name'},
               linkto=URL(r=request,f='table/db/')
        """

        self.ignore_rw = ignore_rw
        nbsp = XML('&nbsp;') # Firefox2 does not display fields with blanks
        FORM.__init__(self, *[], **attributes)
        ofields = fields
        if fields == None:
            fields = [f for f in table.fields if \
                      ignore_rw or table[f].writable or table[f].readable]
        self.fields = fields
        if not 'id' in self.fields:
            self.fields.insert(0, 'id')
        self.table = table
        if record and isinstance(record, (int, long, str, unicode)):
            records = table._db(table.id == record).select()
            if records:
                record = records[0]
            else:
                record = None
        self.record = record
        self.record_id = None
        self.trows = {}
        xfields = []
        self.fields = fields
        self.custom = Storage()
        self.custom.dspval = Storage()
        self.custom.inpval = Storage()
        self.custom.label = Storage()
        for fieldname in self.fields:
            if fieldname.find('.') >= 0:
                continue
            field = self.table[fieldname]
            if comments:
                comment = col3.get(fieldname, field.comment) or ''
            else:
                comment = ''
            if labels != None and fieldname in labels:
                label = labels[fieldname]
            else:
                label = str(field.label) + ': '
            self.custom.label[fieldname] = label
            field_id = '%s_%s' % (table._tablename, fieldname)
            label = LABEL(label, _for=field_id, _id='%s__label' % field_id)
            row_id = field_id + '__row'
            if fieldname == 'id':
                self.custom.dspval.id = nbsp
                self.custom.inpval.id = ''
                if record:
                    if showid and 'id' in fields and field.readable:
                        v = record['id']
                        self.custom.dspval.id = str(v)
                        xfields.append(TR(label, SPAN(v, _id=field_id), 
                                          comment, _id='id__row'))
                    self.record_id = str(record['id'])
                continue
            if record:
                default = record[fieldname]
            else:
                default = field.default
            cond = readonly or \
                (not ignore_rw and not field.writable and field.readable)
            if default and not cond:
                default = field.formatter(default)
            dspval = default
            inpval = default
            if cond:

                # ## if field.represent is available else
                # ## ignore blob and preview uploaded images
                # ## format everything else

                if field.represent:
                    inp = field.represent(default)
                elif field.type in ['blob']:
                    continue
                elif field.type == 'upload':
                    inp = UploadWidget.represent(field, default, upload)
                else:
                    inp = field.formatter(default)
            elif hasattr(field, 'widget') and field.widget:
                inp = field.widget(field, default)
            elif field.type == 'upload':
                inp = self.widgets.upload.widget(field, default, upload)
            elif field.type == 'boolean':
                inp = self.widgets.boolean.widget(field, default)
                if default:
                    inpval = 'checked'
                else:
                    inpval = ''
            elif OptionsWidget.has_options(field):
                if not field.requires.multiple:
                    inp = self.widgets.options.widget(field, default)
                else:
                    inp = self.widgets.multiple.widget(field, default)
                if fieldname in keepopts:
                    inpval = TAG[''](*inp.components)
            elif field.type == 'text':
                inp = self.widgets.text.widget(field, default)
            elif field.type == 'password':
                inp = self.widgets.password.widget(field, default)
                if self.record:
                    dspval = '********'
                else:
                    dspval = ''
            elif field.type == 'blob':
                continue
            else:
                inp = self.widgets.string.widget(field, default)
            tr = self.trows[fieldname] = TR(label, inp, comment,
                    _id=row_id)
            xfields.append(tr)
            self.custom.dspval[fieldname] = dspval or nbsp
            self.custom.inpval[fieldname] = inpval or ''
        if record and linkto:
            for (rtable, rfield) in table._referenced_by:
                query = urllib.quote(str(table._db[rtable][rfield]
                         == record.id))
                lname = olname = '%s.%s' % (rtable, rfield)
                if ofields and not olname in ofields:
                    continue
                if labels and lname in labels:
                    lname = labels[lname]
                xfields.append(TR('', A(lname, _class='reference',
                                  _href='%s/%s?query=%s' % (linkto,
                                  rtable, query)), col3.get(olname, ''
                                  ), _id='%s__row' % olname.replace('.'
                                  , '__')))
        if record and deletable:
            xfields.append(TR(LABEL(delete_label, _for='delete_record',
                           _id='delete_record__label'),
                           INPUT(_type='checkbox', _class='delete',
                           _id='delete_record',
                           _name='delete_this_record'),
                           col3.get('delete_record', ''),
                           _id='delete_record__row'))
        if not readonly:
            xfields.append(TR('', INPUT(_type='submit',
                           _value=submit_button),
                           col3.get('submit_button', ''),
                           _id='submit_record__row'))
        if record:
            if not self['hidden']:
                self['hidden'] = {}
            self['hidden']['id'] = record['id']
        self.components = [TABLE(*xfields)]

    def accepts(
        self,
        request_vars,
        session=None,
        formname='%(tablename)s_%(record_id)s',
        keepvalues=False,
        onvalidation=None,
        ):
        """
        same as FORM.accepts but also does insert, update or delete in SQLDB.
        """


        if self.record:
            formname_id = self.record.id
            record_id = request_vars.get('id', None)
        else:
            formname_id = 'create'
            record_id = None
        if isinstance(record_id, (list, tuple)):
            record_id = record_id[0]

        if formname:
            formname = formname % dict(tablename=self.table._tablename,
                                       record_id=formname_id)

        # ## THIS IS FOR UNIQUE RECORDS, read IS_NOT_IN_DB

        for fieldname in self.fields:
            field = self.table[fieldname]
            requires = field.requires or []
            if not isinstance(requires, (list, tuple)):
                requires = [requires]
            [item.set_self_id(self.record_id) for item in requires
            if hasattr(item, 'set_self_id')]

        # ## END

        fields = {}
        for key in self.vars:
            fields[key] = self.vars[key]
        ret = FORM.accepts(
            self,
            request_vars,
            session,
            formname,
            keepvalues,
            onvalidation,
            )
        auch = record_id and \
               self.errors and \
               request_vars.get('delete_this_record', False)
        # auch is true when user tries to delete a record
        # that does not pass validation, yet it should be deleted 
        if not ret and not auch:
            for fieldname in self.fields:
                field = self.table[fieldname]
                if hasattr(field, 'widget') and field.widget\
                    and fieldname in request_vars:
                    self.trows[fieldname][1].components = \
                        [field.widget(field, request_vars[fieldname])]
                    self.trows[fieldname][1][0].errors = self.errors
            return ret

        if record_id and record_id != self.record_id:
            raise SyntaxError, 'user is tampering with form'

        if request_vars.get('delete_this_record', False):
            self.table._db(self.table.id == self.record.id).delete()
            return True

        for fieldname in self.fields:
            if fieldname == 'id':
                continue
            if not fieldname in self.table:
                continue
            if not self.ignore_rw and not self.table[fieldname].writable:
                continue
            field = self.table[fieldname]
            if field.type == 'boolean':
                if self.vars.get(fieldname, False):
                    fields[fieldname] = True
                else:
                    fields[fieldname] = False
            elif field.type == 'password' and self.record\
                and request_vars.get(fieldname, None) == '********':
                continue  # do not update if password was not changed
            elif field.type == 'upload':
                f = self.vars[fieldname]
                fd = fieldname + '__delete'
                if not isinstance(f, (str, unicode)):
                    filename = os.path.basename(f.filename)
                    m = re_extension.search(filename)
                    e = m and m.group()[1:] or 'txt'
                    source_file = f.file
                else:
                    ### do not know why this happens, it should not
                    (filename, e) = ('file','txt')
                    source_file = cStringIO.StringIO(f)
                if f != '':
                    uuid_key = str(uuid.uuid4()).replace('-', '')[-16:]
                    encoded_filename = base64.b16encode(filename).lower()
                    newfilename = '%s.%s.%s.%s' % \
                        (self.table._tablename, fieldname, uuid_key,
                         encoded_filename)
                    # for backward compatibility since upload field if 128bytes
                    newfilename = newfilename[:122]+'.'+e
                    self.vars['%s_newfilename' % fieldname] = newfilename
                    fields[fieldname] = newfilename
                    if field.uploadfield == True:
                        pathfilename = \
                            os.path.join(self.table._db._folder,
                                '../uploads/', newfilename)
                        dest_file = open(pathfilename, 'wb')
                        shutil.copyfileobj(source_file, dest_file)
                        dest_file.close()
                    elif field.uploadfield:
                        fields[field.uploadfield] = source_file.read()
                elif self.vars.get(fd, False) or not self.record:
                    fields[fieldname] = ''
                else:
                    fields[fieldname] = self.record[fieldname]
                continue
            elif fieldname in self.vars:
                fields[fieldname] = self.vars[fieldname]
            elif field.default == None:
                self.errors[fieldname] = 'no data'
                return False
            if field.type[:9] in ['integer', 'reference']:
                if fields[fieldname] != None:
                    fields[fieldname] = int(fields[fieldname])
            elif field.type == 'double':
                if fields[fieldname] != None:
                    fields[fieldname] = float(fields[fieldname])
        for fieldname in self.vars:
            if fieldname != 'id' and fieldname in self.table.fields\
                 and not fieldname in fields and not fieldname\
                 in request_vars:
                fields[fieldname] = self.vars[fieldname]
        if record_id:
            self.vars.id = self.record.id
            if fields:
                self.table._db(self.table.id==self.record.id).update(**fields)
                ### should really be 
                # self.table[record_id] = fields
                ### but on mysql update seems to return none
        else:
            self.vars.id = self.table.insert(**fields)
        return ret


class SQLTABLE(TABLE):

    """
    given a SQLRows object, as returned by a db().select(), generates
    an html table with the rows.

    optional arguments:
    linkto: URL to edit individual records
    upload: URL to download uploaded files
    orderby: Add an orderby link to column headers.
    headers: dictionary of headers to headers redefinions
    truncate: length at which to truncate text in table cells.
              Defaults to 16 characters.
    optional names attributes for passed to the <table> tag
    """

    def __init__(
        self,
        sqlrows,
        linkto=None,
        upload=None,
        orderby=None,
        headers={},
        truncate=16,
        **attributes
        ):
        TABLE.__init__(self, **attributes)
        self.components = []
        self.attributes = attributes
        self.sqlrows = sqlrows
        (components, row) = (self.components, [])
        if not orderby:
            for c in sqlrows.colnames:
                row.append(TH(headers.get(c, c)))
        else:
            for c in sqlrows.colnames:
                row.append(TH(A(headers.get(c, c), _href='?orderby='
                            + c)))
        components.append(THEAD(TR(*row)))
        tbody = []
        for (rc, record) in enumerate(sqlrows):
            row = []
            if rc % 2 == 0:
                _class = 'even'
            else:
                _class = 'odd'
            for colname in sqlrows.colnames:
                if not table_field.match(colname):
                    r = record._extra[colname]
                    row.append(TD(r))
                    continue
                (tablename, fieldname) = colname.split('.')
                field = sqlrows._db[tablename][fieldname]
                if tablename in record and isinstance(record,
                        SQLStorage) and isinstance(record[tablename],
                        SQLStorage):
                    r = record[tablename][fieldname]
                elif fieldname in record:
                    r = record[fieldname]
                else:
                    raise SyntaxError, \
                        'something wrong in SQLRows object'
                if field.represent:
                    r = field.represent(r)
                    row.append(TD(r))
                    continue
                if field.type == 'blob' and r:
                    row.append(TD('DATA'))
                    continue
                r = str(field.formatter(r))
                if upload and field.type == 'upload' and r != None:
                    if r:
                        row.append(TD(A('file', _href='%s/%s'
                                    % (upload, r))))
                    else:
                        row.append(TD())
                    continue
                ur = unicode(r, 'utf8')
                if len(ur) > truncate:
                    r = ur[:truncate - 3].encode('utf8') + '...'
                if linkto and field.type == 'id':
                    row.append(TD(A(r, _href='%s/%s/%s' % (linkto,
                               tablename, r))))
                elif linkto and field.type[:9] == 'reference':
                    row.append(TD(A(r, _href='%s/%s/%s' % (linkto,
                               field.type[10:], r))))
                else:
                    row.append(TD(r))
            tbody.append(TR(_class=_class, *row))
        components.append(TBODY(*tbody))


def form_factory(*fields, **attributes):
    return SQLFORM(SQLDB(None).define_table('no_table', *fields),
                   **attributes)


