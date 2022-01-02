# -*- coding: utf-8 -*-
{
    'name': "Hiboutik Connector",
    'description': """
        Connect Odoo with Hiboutik POS
    """,
    'author': "Zuher ELMAS",
    'category': 'Z Modules Account',
    'version': '0.1',
    'depends': ['base', 'point_of_sale'],
    'installable': True,
    'data': [
        # 'security/ir.model.access.csv',
        'views/account.xml',
        'views/pos.xml',
        'views/res_company.xml',
        'views/product.xml',
    ],
    "license": "AGPL-3",
}
