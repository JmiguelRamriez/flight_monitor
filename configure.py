
import yaml
import os

CONFIG_PATH = "config.yaml"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: No existe {CONFIG_PATH}")
        return None
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    print(" Configuración guardada exitosamente.")

def main():
    print("--- Configuración de Monitor de Vuelos ---")
    config = load_config()
    if not config: return

    current_dest = config['travel']['destination_country']
    print(f"\nDestino actual: {current_dest}")
    
    new_dest = input("Ingresa el nuevo código de destino (ej. MAD, NYC, PAR, JP): ").strip().upper()
    
    if new_dest:
        if len(new_dest) < 2:
            print(" El código debe tener al menos 2 letras (ej. MX, US) o 3 para ciudades (ej. TYO).")
        else:
            config['travel']['destination_country'] = new_dest
            # Resetear a default si se cambió
            config['travel']['destination_airports_limit'] = 6 
            save_config(config)
            print(f" Destino actualizado a: {new_dest}")
    else:
        print("Sin cambios.")

    print("\n¿Quieres cambiar algo más?")
    # Future: Add dates/budget options here
    
    input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    main()
