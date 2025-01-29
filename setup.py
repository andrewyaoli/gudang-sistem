from setuptools import setup, find_packages

setup(
    name="warehouse-system",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'flask-sqlalchemy',
        'werkzeug',
        'xlsxwriter',
        'gunicorn',
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A warehouse management system",
    keywords="warehouse, inventory, management",
    python_requires='>=3.6',
)