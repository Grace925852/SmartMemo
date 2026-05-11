import os

base_path = "scripts_ia"
modules = ["approval", "archive", "assignment", "recommandation", "submission"]

def patch_script(module):
    module_dir = os.path.join(base_path, module)
    if not os.path.exists(module_dir): return

    output_dir = f"../../ia_models/{module}"
    
    for f_name in os.listdir(module_dir):
        if not f_name.endswith(".py"): continue
        p = os.path.join(module_dir, f_name)
        
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Nettoyage ASCII
        content = content.encode("ascii", "ignore").decode("ascii")

        # Remplacement des chemins
        content = content.replace('"modeles/', f'"{output_dir}/')
        content = content.replace("'modeles/", f"'{output_dir}/")
        
        # S'assurer que le dossier existe
        if "joblib.dump" in content or "json.dump" in content or "np.save" in content:
            if "import os" not in content:
                content = "import os\n" + content
            if f'os.makedirs("{output_dir}"' not in content:
                content = content.replace("import os", f'import os\nos.makedirs("{output_dir}", exist_ok=True)', 1)

        with open(p, "w", encoding="ascii") as f:
            f.write(content)
    print(f"[OK] {module} patched.")

for mod in modules:
    patch_script(mod)
