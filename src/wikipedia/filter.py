INVALID_PREFIXES = [

    "Kategori:",

    "Category:",

    "File:",

    "Dosya:",

    "Template:",

    "Şablon:",

    "Wikipedia:",

    "Vikipedi:",

    "Help:",

    "Yardım:",

    "Portal:",

]


def keep(title):

    for prefix in INVALID_PREFIXES:

        if title.startswith(prefix):

            return False

    return True