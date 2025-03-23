from flask import current_app, Blueprint, url_for, request, jsonify, render_template_string
from markupsafe import Markup
from wtforms import TextAreaField
from wtforms.widgets import TextArea

class CKEditor(object):
    """The CKEditor class."""

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the CKEditor extension."""
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['ckeditor'] = self
        app.config.setdefault('CKEDITOR_SERVE_LOCAL', False)
        app.config.setdefault('CKEDITOR_PKG_TYPE', 'standard')
        app.config.setdefault('CKEDITOR_LANGUAGE', '')
        app.config.setdefault('CKEDITOR_HEIGHT', 400)
        app.config.setdefault('CKEDITOR_WIDTH', None)
        app.config.setdefault('CKEDITOR_CODE_THEME', 'monokai_sublime')
        app.config.setdefault('CKEDITOR_FILE_UPLOADER', None)
        app.config.setdefault('CKEDITOR_FILE_BROWSER', None)
        app.config.setdefault('CKEDITOR_ENABLE_CODESNIPPET', False)
        app.config.setdefault('CKEDITOR_ENABLE_CSRF', False)
        app.config.setdefault('CKEDITOR_EXTRA_PLUGINS', [])

        blueprint = Blueprint('ckeditor', __name__,
                           static_folder='static',
                           static_url_path='/ckeditor' + app.static_url_path)
        app.register_blueprint(blueprint)

    @staticmethod
    def load(custom_url=None, pkg_type=None, version='4.9.2'):
        """Load CKEditor resource."""
        if custom_url:
            url = custom_url
        else:
            if pkg_type is None:
                pkg_type = current_app.config['CKEDITOR_PKG_TYPE']
            if current_app.config['CKEDITOR_SERVE_LOCAL']:
                url = url_for('ckeditor.static',
                            filename='%s/ckeditor.js' % pkg_type)
            else:
                url = 'https://cdn.ckeditor.com/%s/%s/ckeditor.js' % (version, pkg_type)
        return Markup('<script src="%s"></script>' % url)

    @staticmethod
    def config(name='ckeditor', language=None, height=None, width=None,
              code_theme=None, enable_codesnippet=None, extra_plugins=None, **kwargs):
        """Config CKEditor."""
        extra_plugins = extra_plugins or []
        if enable_codesnippet or current_app.config['CKEDITOR_ENABLE_CODESNIPPET']:
            extra_plugins.append('codesnippet')

        if language is None:
            language = current_app.config['CKEDITOR_LANGUAGE']
        if height is None:
            height = current_app.config['CKEDITOR_HEIGHT']
        if width is None:
            width = current_app.config['CKEDITOR_WIDTH']
        if code_theme is None:
            code_theme = current_app.config['CKEDITOR_CODE_THEME']

        extra_plugins.extend(current_app.config['CKEDITOR_EXTRA_PLUGINS'])

        config_body = '''
        CKEDITOR.replace( "%s", {
            language: "%s",
            height: %s,
            width: "%s",
            codeSnippet_theme: "%s",
            extraPlugins: "%s"
        });
        ''' % (
            name, language, height,
            width if width else 'auto',
            code_theme, ','.join(extra_plugins)
        )
        return Markup(config_body)

    @staticmethod
    def create(name='ckeditor', value=''):
        """Create a CKEditor textarea."""
        return Markup('''<textarea name="%s">%s</textarea>''' % (name, value))

    @staticmethod
    def load_code_theme():
        """Load code theme css."""
        theme = current_app.config['CKEDITOR_CODE_THEME']
        if theme == 'default':
            theme = 'monokai_sublime'
        return Markup('''<link href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.12.0/styles/%s.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.12.0/highlight.min.js"></script>
        <script>hljs.initHighlightingOnLoad();</script>''' % theme)

class CKEditorField(TextAreaField):
    """Form field for CKEditor."""

    def __init__(self, label=None, validators=None, **kwargs):
        super(CKEditorField, self).__init__(label, validators, **kwargs) 