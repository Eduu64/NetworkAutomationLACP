#!/usr/bin/env python3
"""
LACP RESILIENCY VALIDATOR - DEMO VERSION
Demostración con datos simulados para pruebas sin dispositivos reales
"""

from lacp_validator import (
    LACPResiliencyValidator, 
    PortChannelValidation, 
    ResiliencyStatus
)


# Datos simulados de etherchannel
SIMULATED_DATA_IOS_XE = {
    'switch_core_1': {
        'interfaces': {
            'Port-channel1': {
                'protocol': 'lacp',
                'bundle': True,
                'members': {
                    'GigabitEthernet1/0/1': {
                        'bundled': True,
                        'status': 'ok',
                        'lacp_mode': 'active'
                    },
                    'GigabitEthernet2/0/1': {
                        'bundled': True,
                        'status': 'ok',
                        'lacp_mode': 'active'
                    }
                }
            },
            'Port-channel2': {
                'protocol': 'lacp',
                'bundle': False,
                'members': {
                    'GigabitEthernet1/0/2': {
                        'bundled': True,
                        'status': 'ok',
                        'lacp_mode': 'active'
                    },
                    'GigabitEthernet1/0/3': {
                        'bundled': True,
                        'status': 'ok',
                        'lacp_mode': 'active'
                    },
                    'GigabitEthernet1/0/4': {
                        'bundled': False,
                        'status': 'down',
                        'lacp_mode': 'active'
                    }
                }
            }
        }
    }
}

SIMULATED_DATA_NX_OS = {
    'switch_nx_1': {
        'interfaces': {
            'port-channel10': {
                'protocol': 'lacp',
                'members': {
                    'Ethernet1/1': {
                        'bundled': True,
                        'status': 'ok',
                        'lacp_mode': 'active'
                    },
                    'Ethernet2/1': {
                        'bundled': True,
                        'status': 'ok',
                        'lacp_mode': 'active'
                    }
                }
            },
            'port-channel11': {
                'protocol': 'pagp',
                'members': {
                    'Ethernet1/5': {
                        'bundled': True,
                        'status': 'ok',
                        'lacp_mode': None
                    },
                    'Ethernet1/6': {
                        'bundled': True,
                        'status': 'ok',
                        'lacp_mode': None
                    }
                }
            }
        }
    }
}


class MockDevice:
    """Mock dispositivo para pruebas sin SSH"""
    
    def __init__(self, name, simulated_data):
        self.name = name
        self.simulated_data = simulated_data
    
    def learn(self, feature):
        if feature == 'etherchannel':
            return self.simulated_data.get('interfaces', {})
        return {}
    
    def disconnect(self):
        pass


class LACPResiliencyValidatorDemo(LACPResiliencyValidator):
    """Versión demo con datos simulados"""
    
    def load_testbed(self):
        print(f"\n[DEMO] Usando datos simulados (sin SSH)")
        return True
    
    def connect_to_devices(self, device_names=None):
        print(f"\n[DEMO] Creando dispositivos mock...")
        
        all_devices = {
            'switch_core_1': MockDevice(
                'switch_core_1', 
                SIMULATED_DATA_IOS_XE['switch_core_1']
            ),
            'switch_nx_1': MockDevice(
                'switch_nx_1',
                SIMULATED_DATA_NX_OS['switch_nx_1']
            )
        }
        
        target_devices = device_names if device_names else list(all_devices.keys())
        connected = {k: v for k, v in all_devices.items() if k in target_devices}
        
        print(f"[DEMO] {len(connected)} dispositivo(s) mock:")
        for dev_name in connected.keys():
            print(f"  ├─ {dev_name}... ✓")
        
        return connected, []
    
    def learn_etherchannel(self, device):
        print(f"\n[DEMO] Aprendiendo etherchannel en {device.name}...", end=" ", flush=True)
        result = {'interfaces': device.simulated_data}
        print("✓")
        return result


def run_demo():
    print("""
╔════════════════════════════════════════════════════════════════╗
║     LACP RESILIENCY VALIDATOR - DEMO MODE                     ║
║     Datos simulados (SIN conexión SSH)                        ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    validator = LACPResiliencyValidatorDemo("testbed.yaml")
    
    try:
        print("\n" + "="*70)
        print("VALIDACIÓN DE DEMOSTRACIÓN")
        print("="*70)
        
        if not validator.load_testbed():
            return False
        
        devices, errors = validator.connect_to_devices()
        
        if not devices:
            return False
        
        all_results = {}
        for device_name, device in devices.items():
            results = validator.validate_device(device)
            all_results[device_name] = results
            try:
                device.disconnect()
            except:
                pass
        
        validator.results = all_results
        validator.generate_summary_report(all_results)
        
        # Análisis
        print("\n" + "="*70)
        print("INTERPRETACIÓN DE RESULTADOS")
        print("="*70 + """

1. switch_core_1 (IOS-XE)
   
   ✓ Port-channel1: PASSED
     • 2/2 miembros up (Gi1/0/1, Gi2/0/1)
     • LACP active en ambas
     • Slots diferentes: [1, 2]
     → RESILIENTE ✓
   
   ✗ Port-channel2: FAILED
     • Solo 1/3 miembros up (Gi1/0/4 down)
     • TODOS en MISMO slot: [1]
     → PROBLEMAS CRÍTICOS:
       - Falta redundancia
       - Falta distribución hardware


2. switch_nx_1 (NX-OS)
   
   ✓ port-channel10: PASSED
     • 2/2 miembros up
     • LACP active
     • Slots diferentes: [1, 2]
     → RESILIENTE ✓
   
   ⚠ port-channel11: WARNING
     • 2/2 miembros pero...
     • PROTOCOLO: PAgP (NO LACP)
     → Recomendar migración a LACP


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONCEPTOS DE RESILIENCIA LACP:

✓ REDUNDANCIA: Mínimo 2 interfaces en estado up
✓ DISTRIBUCIÓN: Miembros en DIFERENTES slots (Gi1/x vs Gi2/x)
✓ PROTOCOLO: LACP en modo 'active' para detección dinámica

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CÓMO FUNCIONA CON DISPOSITIVOS REALES:

1. pip install pyats genie pyyaml

2. Configurar testbed.yaml:
   
   devices:
     switch-core:
       type: switch
       os: iosxe
       connections:
         cli:
           protocol: ssh
           ip: 10.0.1.10
       credentials:
         default:
           username: admin
           password: password123

3. python lacp_validator.py
   (Automáticamente conecta y valida dispositivos reales)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = run_demo()
    sys.exit(0 if success else 1)
