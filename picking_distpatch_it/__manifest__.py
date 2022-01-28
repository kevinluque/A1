# -*- coding: utf-8 -*-
{
    'name': "Picking Distpatch IT",

    'summary': """""",

    'description': """
        Picking Distpatch IT
    """,

    'author': "ITGRUPO",
    'category': 'Uncategorized',
    'version': '1.0',
    'depends': ['base','sale','mail','fleet','query_ruc_dni','remission_guide_it'],
    'data': [
        'security/ir.model.access.csv',
        'security/secuencias.xml',
        'views/picking_distpatch.xml',
        'views/fleet_vehicle.xml',
        'report/picking_distpatch_report.xml'
    ],
    'demo': [],
}
