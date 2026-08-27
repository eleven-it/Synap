from mtrix.extractors.base import ExportConfig


def export_cfg_test(**kwargs) -> ExportConfig:
    data = {
        "base_empresa": "empresa_test",
        "fecha_desde": "2026-08-01",
        "fecha_hasta": "2026-08-12",
        "proveedores": ["TODOS"],
        "cnpj_fornecedor": "30712345678",
        "cnpj_distribuidor": "20111111112",
        "razon_social_fornecedor": "DISTRIBUIDORA TEST",
        "pvnf": False,
        "multiplicador_cantidad": 1,
        "multiplicador_precio": 1,
        "fecha_archivo": "20260812",
    }
    data.update(kwargs)
    return ExportConfig(**data)
