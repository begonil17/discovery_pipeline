BLOCKED_NAMESPACES = {
    "book",
    "category",
    "category talk",
    "draft",
    "file",
    "file talk",
    "gadget",
    "gadget definition",
    "help",
    "help talk",
    "media",
    "mediawiki",
    "module",
    "portal",
    "portal talk",
    "project",
    "special",
    "talk",
    "template",
    "template talk",
    "timedtext",
    "topic",
    "user",
    "user talk",
    "dosya",
    "dosya tartışma",
    "kategori",
    "kategori tartışma",
    "kitap",
    "konu",
    "kullanıcı",
    "kullanıcı mesaj",
    "mediawiki tartışma",
    "medya",
    "modül",
    "portal tartışma",
    "taslak",
    "tartışma",
    "vikipedi",
    "vikipedi tartışma",
    "yardım",
    "yardım tartışma",
    "şablon",
    "şablon tartışma",
    "özel",
}


def keep(title):

    if not title or not title.strip():
        return False

    namespace, separator, _ = title.partition(":")

    if (
        separator
        and namespace.strip().casefold()
        in BLOCKED_NAMESPACES
    ):
        return False

    return True
