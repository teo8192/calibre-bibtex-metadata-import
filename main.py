#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai

if False:
    # This is here to keep my python error checker from complaining about
    # the builtin functions that will be defined by the plugin loading system
    # You do not need this code in your plugins
    get_icons = get_resources = None

from qt.core import QDialog, QVBoxLayout, QPushButton, QMessageBox, QLabel, QFileDialog

from calibre_plugins.bibtex_metadata_import.config import prefs


class DemoDialog(QDialog):

    def __init__(self, gui, icon, do_user_config):
        QDialog.__init__(self, gui)
        self.gui = gui
        self.do_user_config = do_user_config

        # The current database shown in the GUI
        # db is an instance of the class LibraryDatabase from db/legacy.py
        # This class has many, many methods that allow you to do a lot of
        # things. For most purposes you should use db.new_api, which has
        # a much nicer interface from db/cache.py
        self.db = gui.current_db

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        self.setWindowTitle('Bibtex Metadata Import')
        self.setWindowIcon(icon)

        self.file_name_label = QLabel('')
        self.l.addWidget(self.file_name_label)

        self.file_name_button = QPushButton('Set Bibtex file', self)
        self.file_name_button.clicked.connect(self.set_bibtex_file)
        self.l.addWidget(self.file_name_button)

        self.update_metadata_button = QPushButton(
            'Update metadata in a book\'s files', self)
        self.update_metadata_button.clicked.connect(self.update_metadata)
        self.l.addWidget(self.update_metadata_button)

        self.resize(self.sizeHint())

    def set_bibtex_file(self):
        file = QFileDialog.getOpenFileName(self, 'Open file', None, 'Bibtex File (*.bib)')

        if not file[0]:
            from calibre.gui2 import error_dialog

            error_dialog(self, 'Error', 'No file selected', show=True)
            return

        self.file_name_label.setText(file[0])

    def bibtex(self):
        if not self.file_name_label.text() or self.file_name_label.text() == '':
            from calibre.gui2 import error_dialog

            error_dialog(self, 'Error', 'No file selected', show=True)
            return None

        import re
        kv = re.compile(r'\b(?P<key>\w+)[ \t]*=[ \t]*{(?P<value>[^}]+)}')
        citation = {}
        with open(self.file_name_label.text(), 'r') as f:
            for line in f:
                # info dialog with the line
                for match in kv.finditer(line):
                    citation[match.group('key')] = match.group('value')


        if citation == {}:
            error_dialog(self, 'Error', 'Found no info in the bibtex file', show=True)
            return None
        return citation

    def update_metadata(self):
        '''
        Set the metadata in the files in the selected book's record to
        match the current metadata in the database.
        '''
        from calibre.ebooks.metadata.meta import set_metadata
        from calibre.gui2 import error_dialog, info_dialog

        citation = self.bibtex()
        if not citation:
            return

        # Get currently selected books
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return error_dialog(self.gui, 'Cannot update metadata',
                             'No books selected', show=True)
        # Map the rows to book ids
        ids = list(map(self.gui.library_view.model().id, rows))
        db = self.db.new_api
        for book_id in ids:
            # Get the current metadata for this book from the db
            mi = db.get_metadata(book_id, get_cover=True, cover_as_data=True)
            mi.title = citation['title']

            from calibre.ebooks.metadata import title_sort, author_to_author_sort

            mi.title_sort = title_sort(mi.title)

            # need to proccess the authors file
            def fix_author(author):
                if ',' in author:
                    author = author.split(',')
                    author = author[1].strip() + ' ' + author[0].strip()
                return author

            mi.authors = list(map(fix_author, citation['author'].split(' and ')))
            mi.authors_sort = list(map(lambda author : author_to_author_sort(fix_author(author)), citation['author'].split(' and ')))

            db.set_metadata(book_id, mi, set_title=True, set_authors=True)

        info_dialog(self, 'Updated files',
                'Updated the metadata in the files of %d book(s)'%len(ids),
                show=True)
