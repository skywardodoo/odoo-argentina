import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _iter_account_tag_fk_references(cr):
    """Return all FK references that point to account_account_tag."""
    cr.execute(
        """
        SELECT n.nspname, c.relname, a.attname
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN unnest(con.conkey) AS k(attnum) ON TRUE
        JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum
        WHERE con.contype = 'f'
          AND con.confrelid = 'account_account_tag'::regclass
        """
    )
    return cr.fetchall()


def _is_account_tag_referenced(cr, references, tag_id):
    """Check if a given account.account.tag is still referenced by any FK table."""
    for schema, table, column in references:
        query = 'SELECT 1 FROM "{}"."{}" WHERE "{}" = %s LIMIT 1'.format(
            schema.replace('"', '""'),
            table.replace('"', '""'),
            column.replace('"', '""'),
        )
        cr.execute(query, (tag_id,))
        if cr.fetchone():
            return True
    return False


def migrate(cr, version):
    """Las account_account_tags ya no las usamos en 19 y por lo tanto las eliminamos
    ver  commit relacionado en https://github.com/ingadhoc/odoo-argentina/commit/63d2dd6eaab9cdadfb81a7f466d1c76d39aad7a9
    Pero para el caso de los clientes que migran donde ya estan usando esas etiquetas no
    las podemos borrar, por eso implementamos este script que elimina el XML ID de etiquetas
    en uso, asi quedan las etiquetas y evitamos se borren las account_account_tags que estan
    en uso"""
    env = api.Environment(cr, SUPERUSER_ID, {})

    xml_id_names = [
        "tag_a_cuenta_ganancias",
        "tag_a_cuenta_iva",
        "tag_iva_primer_parrafo",
        "tag_unaffected_earnings",
        "tag_impuestos_a_las_ganancias",
        "tag_liquidacion_de_iva",
        "tag_liquidacion_de_iibb",
        "tag_liquidacion_de_ganancias",
        "tag_liquidacion_sicore_aplicado",
        "tag_liquidacion_iibb_aplicado",
        "tax_tag_a_cuenta_suss",
        "tax_tag_a_cuenta_iibb",
        "tax_tag_a_cuenta_ganancias",
        "tax_tag_a_cuenta_iva",
        "tag_ret_perc_iibb_aplicada",
        "tag_ret_perc_sicore_aplicada",
    ]
    # Jurisdiction tax tags were deprecated previously; keep them if they are
    # still linked to tax repartition lines in migrated databases.
    xml_id_names += [f"tag_tax_jurisdiccion_{code}" for code in range(901, 925)]
    account_tag_fk_refs = _iter_account_tag_fk_references(cr)
    for xml_id_name in xml_id_names:
        account_tag_id = env.ref(f"l10n_ar_ux.{xml_id_name}", raise_if_not_found=False)
        if account_tag_id:
            if _is_account_tag_referenced(cr, account_tag_fk_refs, account_tag_id.id):
                _logger.info(f"Eliminamos el extenal ref l10n_ar_ux.{xml_id_name} ya que se encuentra en uso")
                cr.execute(
                    """
                    DELETE FROM ir_model_data
                    WHERE module = 'l10n_ar_ux' AND name = %s
                """,
                    (xml_id_name,),
                )
