#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para aplicar indices recomendados y ejecutar EXPLAIN antes/despues.
Entorno: adminerp_copy (pruebas)
"""

import mysql.connector
from mysql.connector import Error
import json
from datetime import datetime

# Configuracion (localhost - adminerp_copy)
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'admin123.',
    'database': 'adminerp_copy'
}

# Consultas criticas para EXPLAIN (simplificadas para evitar errores de columnas)
EXPLAIN_QUERIES = [
    {
        'name': 'Q1_margen_por_operacion',
        'sql': """
            SELECT SUM(total_venta) FROM vw_margen_comanda WHERE id_operacion = 1130
        """
    },
    {
        'name': 'Q2_consumo_valorizado',
        'sql': """
            SELECT id_operacion, SUM(costo_consumo) AS costo
            FROM vw_consumo_valorizado_operativa WHERE id_operacion = 1130
            GROUP BY id_operacion
        """
    },
    {
        'name': 'Q3_comandas_ventas_activas',
        'sql': """
            SELECT COUNT(*) FROM bar_comanda WHERE id_operacion = 1130
        """
    },
    {
        'name': 'Q4_comandas_states_filter',
        'sql': """
            SELECT COUNT(*) FROM bar_comanda
            WHERE estado = 'VEN' AND estado_comanda = 2 AND estado_impresion = 2
        """
    }
]

# Indices recomendados
RECOMMENDED_INDEXES = [
    # Criticos (MUST)
    {
        'table': 'bar_comanda',
        'name': 'idx_bar_comanda_op_fecha',
        'sql': 'ALTER TABLE bar_comanda ADD INDEX idx_bar_comanda_op_fecha (id_operacion, fecha)',
        'priority': 'MUST'
    },
    {
        'table': 'bar_comanda',
        'name': 'idx_bar_comanda_estados',
        'sql': 'ALTER TABLE bar_comanda ADD INDEX idx_bar_comanda_estados (estado, estado_comanda, estado_impresion)',
        'priority': 'MUST'
    },
    {
        'table': 'bar_detalle_comanda_salida',
        'name': 'idx_detalle_comanda_producto',
        'sql': 'ALTER TABLE bar_detalle_comanda_salida ADD INDEX idx_detalle_comanda_producto (id_comanda, id_producto)',
        'priority': 'MUST'
    },
    # Opcionales (SHOULD)
    {
        'table': 'alm_producto',
        'name': 'idx_alm_producto_estado',
        'sql': 'ALTER TABLE alm_producto ADD INDEX idx_alm_producto_estado (estado)',
        'priority': 'SHOULD'
    },
    {
        'table': 'ope_operacion',
        'name': 'idx_ope_operacion_estado',
        'sql': 'ALTER TABLE ope_operacion ADD INDEX idx_ope_operacion_estado (estado, estado_operacion)',
        'priority': 'SHOULD'
    },
    {
        'table': 'parameter_table',
        'name': 'idx_parameter_master_estado',
        'sql': 'ALTER TABLE parameter_table ADD INDEX idx_parameter_master_estado (id_master, estado)',
        'priority': 'SHOULD'
    }
]


def execute_query(cursor, query):
    """Ejecuta una consulta y retorna resultados."""
    cursor.execute(query)
    return cursor.fetchall()


def get_existing_indexes(cursor, table_name):
    """Obtiene indices existentes para una tabla."""
    query = f"""
        SELECT INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}'
        GROUP BY INDEX_NAME
    """
    cursor.execute(query)
    return {row[0]: row[1] for row in cursor.fetchall()}


def run_explain(cursor, query_name, sql):
    """Ejecuta EXPLAIN y retorna resultado."""
    explain_sql = f"EXPLAIN {sql.strip()}"
    cursor.execute(explain_sql)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    
    result = {
        'query': query_name,
        'plan': []
    }
    
    for row in rows:
        result['plan'].append(dict(zip(columns, row)))
    
    return result


def main():
    print("=" * 80)
    print("APLICACION DE INDICES Y VALIDACION CON EXPLAIN")
    print("Entorno: adminerp_copy (pruebas)")
    print("Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)
    print()
    
    try:
        # Conectar
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("✓ Conectado a adminerp_copy")
        print()
        
        # PASO 1: Ejecutar EXPLAIN ANTES de aplicar indices
        print("=" * 80)
        print("PASO 1: EXPLAIN ANTES (baseline)")
        print("=" * 80)
        print()
        
        explain_before = []
        for query_info in EXPLAIN_QUERIES:
            print(f"Ejecutando EXPLAIN para: {query_info['name']}")
            result = run_explain(cursor, query_info['name'], query_info['sql'])
            explain_before.append(result)
            
            # Mostrar resumen
            for plan_row in result['plan']:
                extra_val = plan_row.get('Extra') or ''
                print(f"  - type: {plan_row.get('type', 'N/A')}, "
                      f"rows: {plan_row.get('rows', 'N/A')}, "
                      f"Extra: {extra_val[:50] if extra_val else 'N/A'}")
            print()
        
        # PASO 2: Verificar indices existentes
        print("=" * 80)
        print("PASO 2: VERIFICACION DE INDICES EXISTENTES")
        print("=" * 80)
        print()
        
        indexes_to_create = []
        for idx_info in RECOMMENDED_INDEXES:
            existing = get_existing_indexes(cursor, idx_info['table'])
            
            if idx_info['name'] in existing:
                print(f"✓ Ya existe: {idx_info['table']}.{idx_info['name']}")
            else:
                print(f"✗ Faltante: {idx_info['table']}.{idx_info['name']} [{idx_info['priority']}]")
                indexes_to_create.append(idx_info)
        
        print()
        print(f"Total indices faltantes: {len(indexes_to_create)}")
        print()
        
        # PASO 3: Aplicar indices faltantes
        if indexes_to_create:
            print("=" * 80)
            print("PASO 3: APLICANDO INDICES RECOMENDADOS")
            print("=" * 80)
            print()
            
            for idx_info in indexes_to_create:
                try:
                    print(f"Creando: {idx_info['table']}.{idx_info['name']}...")
                    cursor.execute(idx_info['sql'])
                    conn.commit()
                    print(f"  ✓ Creado exitosamente")
                except Error as e:
                    print(f"  ✗ Error: {e}")
                print()
        else:
            print("No hay indices faltantes por aplicar.")
            print()
        
        # PASO 4: Ejecutar EXPLAIN DESPUES de aplicar indices
        print("=" * 80)
        print("PASO 4: EXPLAIN DESPUES (con indices)")
        print("=" * 80)
        print()
        
        explain_after = []
        for query_info in EXPLAIN_QUERIES:
            print(f"Ejecutando EXPLAIN para: {query_info['name']}")
            result = run_explain(cursor, query_info['name'], query_info['sql'])
            explain_after.append(result)
            
            # Mostrar resumen
            for plan_row in result['plan']:
                extra_val = plan_row.get('Extra') or ''
                print(f"  - type: {plan_row.get('type', 'N/A')}, "
                      f"rows: {plan_row.get('rows', 'N/A')}, "
                      f"Extra: {extra_val[:50] if extra_val else 'N/A'}")
            print()
        
        # PASO 5: Comparacion y reporte
        print("=" * 80)
        print("PASO 5: COMPARACION ANTES/DESPUES")
        print("=" * 80)
        print()
        
        for i, query_info in enumerate(EXPLAIN_QUERIES):
            print(f"Consulta: {query_info['name']}")
            print("-" * 40)
            
            before = explain_before[i]['plan'][0] if explain_before[i]['plan'] else {}
            after = explain_after[i]['plan'][0] if explain_after[i]['plan'] else {}
            
            type_before = before.get('type', 'N/A')
            type_after = after.get('type', 'N/A')
            rows_before = before.get('rows', 0) or 0
            rows_after = after.get('rows', 0) or 0
            
            print(f"  type:   {type_before} → {type_after}")
            print(f"  rows:   {rows_before} → {rows_after}")
            
            if rows_before > 0 and rows_after > 0:
                improvement = ((rows_before - rows_after) / rows_before) * 100
                print(f"  mejora: {improvement:.1f}% reduccion en rows")
            
            extra_before = before.get('Extra', '')
            extra_after = after.get('Extra', '')
            if extra_before != extra_after:
                print(f"  Extra antes: {extra_before[:60]}")
                print(f"  Extra despues: {extra_after[:60]}")
            
            print()
        
        # Guardar reporte JSON
        report = {
            'timestamp': datetime.now().isoformat(),
            'environment': 'adminerp_copy',
            'indexes_created': [idx['name'] for idx in indexes_to_create],
            'explain_before': explain_before,
            'explain_after': explain_after
        }
        
        report_file = 'docs/explain_before_after_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✓ Reporte completo guardado en: {report_file}")
        print()
        
        cursor.close()
        conn.close()
        print("✓ Proceso completado exitosamente")
        
    except Error as e:
        print(f"✗ Error de conexion/ejecucion: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
