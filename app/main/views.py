from . import main_blueprint as main


@main.route('/')
def index():
    return 'main.index'