"""
dump_pst_emails.py
-----------------
Extrait TOUS les emails du dossier "archives Lisa" du fichier
Ressources_brutes/backup.pst (archives du helpdesk Religiosoft) vers un
JSON brut local, via Outlook (COM) deja ouvert sur ce poste avec ce PST
attache (mot de passe deja saisi manuellement par l'utilisateur).

Sortie : Ressources_brutes/emails_pst/raw_dump.json (JAMAIS commite -
contient des donnees personnelles reelles non anonymisees, voir
.gitignore). Etape purement technique de recuperation - l'anonymisation,
le regroupement question/reponse et le filtrage se font dans un script
separe (parse_pst_emails.py) pour pouvoir iterer sans re-interroger
Outlook a chaque fois (lent et fragile).

Usage:
    python3 scripts_ponctuels/dump_pst_emails.py
"""
import json
import os

import win32com.client

PST_PATH = os.path.abspath("Ressources_brutes/backup.pst")
FOLDER_NAME = "archives Lisa"
OUT_PATH = "Ressources_brutes/emails_pst/raw_dump.json"


def find_folder(folder, name):
    if folder.Name == name:
        return folder
    for sub in folder.Folders:
        found = find_folder(sub, name)
        if found:
            return found
    return None


def safe_get(item, attr, default=""):
    try:
        val = getattr(item, attr)
        return val if val is not None else default
    except Exception:
        return default


def main():
    outlook = win32com.client.Dispatch("Outlook.Application")
    ns = outlook.GetNamespace("MAPI")

    store = None
    for s in ns.Stores:
        try:
            if s.IsDataFileStore and PST_PATH.lower() in (s.FilePath or "").lower():
                store = s
                break
        except Exception:
            pass
    if store is None:
        ns.AddStore(PST_PATH)
        for s in ns.Stores:
            try:
                if s.IsDataFileStore and PST_PATH.lower() in (s.FilePath or "").lower():
                    store = s
                    break
            except Exception:
                pass
    if store is None:
        raise RuntimeError(f"Impossible de trouver/attacher le store pour {PST_PATH}")

    root = store.GetRootFolder()
    folder = find_folder(root, FOLDER_NAME)
    if folder is None:
        raise RuntimeError(f"Dossier '{FOLDER_NAME}' introuvable dans {PST_PATH}")

    items = folder.Items
    total = items.Count
    print(f"{total} items dans '{FOLDER_NAME}'")

    records = []
    item = items.GetFirst()
    n = 0
    errors = 0
    while item is not None:
        n += 1
        try:
            if item.Class != 43:  # olMail
                item = items.GetNext()
                continue
            received = safe_get(item, "ReceivedTime")
            records.append({
                "index": n,
                "entry_id": safe_get(item, "EntryID"),
                "subject": safe_get(item, "Subject"),
                "sender_name": safe_get(item, "SenderName"),
                "sender_email": safe_get(item, "SenderEmailAddress"),
                "to": safe_get(item, "To"),
                "cc": safe_get(item, "CC"),
                "received_time": str(received) if received else "",
                "conversation_topic": safe_get(item, "ConversationTopic"),
                "conversation_id": str(safe_get(item, "ConversationID")),
                "body": safe_get(item, "Body"),
            })
        except Exception as e:
            errors += 1
            print(f"  ERREUR item {n}: {e}")
        if n % 200 == 0:
            print(f"  {n}/{total} traites...")
        item = items.GetNext()

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"\nOK - {len(records)} emails ecrits dans {OUT_PATH} ({errors} erreurs)")


if __name__ == "__main__":
    main()
