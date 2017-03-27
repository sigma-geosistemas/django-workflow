# coding: utf-8
from setuptools import setup, find_packages

setup(
    name='django-workflow-fsm',
    version='1.0.2',

    description='Maquina de Estados, navega entre estados, executando tasks e habilitando ações a cada estado',
    long_description='Uma Maquina de Estados configurável, que permite navegar entre seus status, disparar tarefas em sua transição e habilitar ações em cada status.',

    author='SIGMA Consultoria',
    author_email='atendimento@consultoriasigma.com.br',
    maintainer_email='atendimento@consultoriasigma.com.br',
    url='https://github.com/sigma-geosistemas/django-workflow/',
    install_requires=[
        "celery",
        "django",
        "django-ordered-model",
        "django-phonenumber-field",
        "djangorestframework",
        "djangorestframework-filters",
        "django-reversion",
        "redis",
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    keywords='fsm workflow',

    classifiers=[
        'Framework :: Django',
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
        'Natural Language :: Portuguese (Brazilian)'
    ],
)
