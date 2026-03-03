#!/usr/bin/env python3
"""
LACP RESILIENCY VALIDATOR - Cisco IOS/IOS-XE/NX-OS
Herramienta de validación de resiliencia de agregación de enlaces usando pyATS/Genie
"""

import sys
import yaml
from typing import Dict, List, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ResiliencyStatus(Enum):
    """Estados posibles en la validación de resiliencia"""
    PASSED = "✓ PASSED"
    FAILED = "✗ FAILED"
    WARNING = "⚠ WARNING"
    UNKNOWN = "? UNKNOWN"


@dataclass
class PortChannelValidation:
    """Resultado de validación de un Port-Channel"""
    device_name: str
    port_channel: str
    status: ResiliencyStatus
    num_members_up: int
    total_members: int
    protocol_type: str
    is_lacp_active: bool
    hardware_distributed: bool
    slots_used: set
    findings: List[str]
    recommendations: List[str]


class LACPResiliencyValidator:
    """
    Validador de resiliencia LACP para dispositivos Cisco.
    Utiliza pyATS para conexión y Genie para parsing estructurado.
    """
    
    MIN_REDUNDANT_MEMBERS = 2
    MIN_SLOTS_FOR_DISTRIBUTION = 2
    
    def __init__(self, testbed_file: str):
        """Inicializa validador con configuración del testbed"""
        self.testbed_file = testbed_file
        self.testbed = None
        self.results: Dict[str, List[PortChannelValidation]] = {}
        
    def load_testbed(self) -> bool:
        """Carga archivo testbed.yaml"""
        try:
            print(f"\n[INFO] Cargando testbed: {self.testbed_file}")
            
            if not Path(self.testbed_file).exists():
                print(f"[ERROR] Archivo no encontrado: {self.testbed_file}")
                return False
            
            with open(self.testbed_file, 'r') as f:
                self.testbed = yaml.safe_load(f)
            
            print(f"[SUCCESS] Testbed cargado")
            devices_list = list(self.testbed.get('devices', {}).keys())
            print(f"[INFO] Dispositivos: {devices_list}")
            return True
            
        except yaml.YAMLError as e:
            print(f"[ERROR] Error YAML: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Error al cargar testbed: {e}")
            return False
    
    def connect_to_devices(self, device_names: List[str] = None) -> Tuple[Dict, List[str]]:
        """
        Conecta a dispositivos usando pyATS.
        
        pyATS carga la topología desde testbed.yaml y gestiona las sesiones SSH.
        """
        from pyats.topology import loader
        
        connected_devices = {}
        errors = []
        
        try:
            topology = loader.load(self.testbed_file)
            target_devices = device_names if device_names else list(topology.devices.keys())
            
            print(f"\n[INFO] Conectando a {len(target_devices)} dispositivo(s)...")
            
            for device_name in target_devices:
                try:
                    device = topology.devices[device_name]
                    print(f"  ├─ {device_name}...", end=" ", flush=True)
                    
                    device.connect(log_stdout=False, 
                                 init_config_commands=[], 
                                 init_exec_commands=[])
                    
                    connected_devices[device_name] = device
                    print("✓")
                    
                except Exception as e:
                    error_msg = f"No se pudo conectar: {str(e)}"
                    print(f"✗")
                    errors.append(error_msg)
            
            if connected_devices:
                print(f"[SUCCESS] {len(connected_devices)} dispositivo(s) conectado(s)")
            
            return connected_devices, errors
            
        except Exception as e:
            print(f"[ERROR] Conexión crítica: {e}")
            errors.append(str(e))
            return {}, errors
    
    def learn_etherchannel(self, device) -> Dict[str, Any]:
        """
        Aprende etherchannel usando Genie.
        
        Genie parsea automáticamente según el OS (IOS/IOS-XE/NX-OS)
        y retorna estructura normalizada:
        
        {
            'interfaces': {
                'Port-channel1': {
                    'name': 'Port-channel1',
                    'protocol': 'lacp',
                    'members': {
                        'GigabitEthernet1/0/1': {
                            'bundled': True,
                            'status': 'ok'
                        }
                    }
                }
            }
        }
        """
        try:
            print(f"\n[INFO] Aprendiendo etherchannel en {device.name}...", end=" ", flush=True)
            
            # device.learn() usa parsers específicos de Genie por SO
            etherchannel_info = device.learn('etherchannel')
            
            print("✓")
            return etherchannel_info
            
        except Exception as e:
            print(f"✗")
            print(f"  [WARN] No se pudo obtener etherchannel: {e}")
            return {}
    
    def parse_interface_slot(self, interface_name: str) -> Tuple[int, int]:
        """
        Extrae slot y puerto del nombre de interfaz Cisco.
        
        Ej: 'GigabitEthernet1/0/1' -> (1, 1)
            'Gi2/0/5' -> (2, 5)
        """
        try:
            iface = interface_name.lower()
            
            # Quitar prefijos comunes
            for prefix in ['gigabitethernet', 'ethernet', 'gi', 'eth', 'e']:
                if iface.startswith(prefix):
                    iface = iface[len(prefix):]
                    break
            
            # Parsear "slot/subif/puerto"
            parts = iface.split('/')
            if len(parts) >= 2:
                slot = int(parts[0])
                puerto = int(parts[-1])
                return slot, puerto
            
        except (ValueError, IndexError):
            pass
        
        return 0, 0
    
    def validate_portchannel(self, device, pc_name: str, 
                           pc_data: Dict[str, Any]) -> PortChannelValidation:
        """
        Valida resiliencia de un Port-Channel.
        
        Criterios:
        1. Redundancia: >= 2 miembros en estado 'up'
        2. Distribución: Miembros en diferentes slots
        3. Protocolo: LACP en modo active
        """
        findings = []
        recommendations = []
        status = ResiliencyStatus.PASSED
        
        protocol = pc_data.get('protocol', 'unknown').lower()
        members = pc_data.get('members', {})
        
        # Contar miembros bundled (up)
        members_up = [
            iface for iface, data in members.items()
            if data.get('bundled', False) or 
               data.get('status', '').lower() == 'up'
        ]
        
        slots_used = set()
        
        # Analizar cada miembro
        for iface_name, iface_data in members.items():
            slot, port = self.parse_interface_slot(iface_name)
            is_bundled = iface_data.get('bundled', False)
            iface_status = iface_data.get('status', 'unknown')
            
            slots_used.add(slot)
            
            if not is_bundled:
                findings.append(
                    f"  ⚠ {iface_name}: No bundled (status: {iface_status})"
                )
        
        # VALIDACIÓN 1: Redundancia
        if len(members_up) < self.MIN_REDUNDANT_MEMBERS:
            status = ResiliencyStatus.FAILED
            findings.append(
                f"  ✗ Solo {len(members_up)}/{len(members)} miembro(s) up "
                f"(mín: {self.MIN_REDUNDANT_MEMBERS})"
            )
            recommendations.append(
                f"Investigar {pc_name}: verificar LACP mode, cables, STP, config"
            )
        else:
            findings.append(
                f"  ✓ Redundancia OK: {len(members_up)}/{len(members)} miembros up"
            )
        
        # VALIDACIÓN 2: Distribución hardware
        unique_slots = len([s for s in slots_used if s != 0])
        hardware_distributed = unique_slots >= self.MIN_SLOTS_FOR_DISTRIBUTION
        
        if not hardware_distributed and len(members) > 1:
            status = ResiliencyStatus.FAILED if status == ResiliencyStatus.PASSED else status
            findings.append(
                f"  ✗ Todos los miembros en el mismo slot/chasis"
            )
            recommendations.append(
                f"Distribuir {pc_name} en diferentes slots/tarjetas. "
                f"Actuales: {sorted(slots_used)}"
            )
        else:
            findings.append(
                f"  ✓ Distribución OK: {unique_slots} slot(s) {sorted(slots_used)}"
            )
        
        # VALIDACIÓN 3: Protocolo LACP
        is_lacp = protocol == 'lacp'
        is_lacp_active = False
        
        if is_lacp:
            lacp_modes = [
                member_data.get('lacp_mode', 'unknown').lower() 
                for member_data in members.values()
            ]
            is_lacp_active = all(m == 'active' for m in lacp_modes if m != 'unknown')
            
            if is_lacp_active:
                findings.append(f"  ✓ LACP en modo active")
            else:
                status = ResiliencyStatus.WARNING if status == ResiliencyStatus.PASSED else status
                findings.append(f"  ⚠ LACP: No todos en modo active")
                recommendations.append(
                    f"Verificar LACP {pc_name}: usar 'channel-group X mode active'"
                )
        else:
            status = ResiliencyStatus.WARNING if status == ResiliencyStatus.PASSED else status
            findings.append(f"  ✗ Protocolo: {protocol.upper()} (no LACP)")
            recommendations.append(
                f"Migrar {pc_name} a LACP para resiliencia dinámica"
            )
        
        return PortChannelValidation(
            device_name=device.name,
            port_channel=pc_name,
            status=status,
            num_members_up=len(members_up),
            total_members=len(members),
            protocol_type=protocol.upper(),
            is_lacp_active=is_lacp_active,
            hardware_distributed=hardware_distributed,
            slots_used=slots_used,
            findings=findings,
            recommendations=recommendations
        )
    
    def validate_device(self, device) -> List[PortChannelValidation]:
        """Valida todos los Port-Channels de un dispositivo"""
        device_results = []
        
        print(f"\n{'='*70}")
        print(f"VALIDANDO: {device.name}")
        print(f"{'='*70}")
        
        etherchannel_info = self.learn_etherchannel(device)
        
        if not etherchannel_info or 'interfaces' not in etherchannel_info:
            print(f"[INFO] No se encontraron Port-Channels")
            return device_results
        
        interfaces_data = etherchannel_info.get('interfaces', {})
        
        if not interfaces_data:
            print(f"[INFO] Ningún Port-Channel encontrado")
            return device_results
        
        print(f"\n[INFO] {len(interfaces_data)} Port-Channel(s) encontrado(s)\n")
        
        # Validar cada Port-Channel
        for pc_name, pc_data in interfaces_data.items():
            validation = self.validate_portchannel(device, pc_name, pc_data)
            device_results.append(validation)
            
            print(f"\n{pc_name}: {validation.status.value}")
            for finding in validation.findings:
                print(finding)
            
            if validation.recommendations:
                print(f"  📋 Recomendaciones:")
                for rec in validation.recommendations:
                    print(f"     → {rec}")
        
        return device_results
    
    def generate_summary_report(self, all_results: Dict[str, List[PortChannelValidation]]):
        """Genera resumen ejecutivo"""
        print(f"\n\n{'='*70}")
        print(f"RESUMEN - VALIDACIÓN RESILIENCIA LACP")
        print(f"{'='*70}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        total_pcs = sum(len(pcs) for pcs in all_results.values())
        total_passed = sum(
            1 for pcs in all_results.values() 
            for pc in pcs if pc.status == ResiliencyStatus.PASSED
        )
        total_failed = sum(
            1 for pcs in all_results.values() 
            for pc in pcs if pc.status == ResiliencyStatus.FAILED
        )
        total_warning = sum(
            1 for pcs in all_results.values() 
            for pc in pcs if pc.status == ResiliencyStatus.WARNING
        )
        
        print(f"Total Port-Channels: {total_passed + total_failed + total_warning}")
        print(f"  ✓ PASSED:  {total_passed}")
        print(f"  ⚠ WARNING: {total_warning}")
        print(f"  ✗ FAILED:  {total_failed}\n")
        
        if total_failed == 0 and total_warning == 0:
            health = "EXCELENTE"
            symbol = "✓"
        elif total_failed == 0:
            health = "BUENA (con advertencias)"
            symbol = "⚠"
        else:
            health = "CRÍTICA"
            symbol = "✗"
        
        print(f"{symbol} Estado General: {health}\n")
        
        # Tabla detalle
        print(f"{'─'*70}")
        print(f"{'DISPOSITIVO':<20} {'PORT-CHANNEL':<18} {'ESTADO':<12} {'RED.':<6}")
        print(f"{'─'*70}")
        
        for device_name, validations in all_results.items():
            for i, val in enumerate(validations):
                device_col = device_name if i == 0 else ""
                red_status = "✓" if val.num_members_up >= 2 else "✗"
                
                print(
                    f"{device_col:<20} {val.port_channel:<18} "
                    f"{val.status.value:<12} {red_status:<6}"
                )
        
        print(f"{'─'*70}")
        
        # Acciones requeridas
        critical_recs = []
        for device_name, validations in all_results.items():
            for val in validations:
                if val.status == ResiliencyStatus.FAILED and val.recommendations:
                    for rec in val.recommendations:
                        critical_recs.append(f"[{val.port_channel}] {rec}")
        
        if critical_recs:
            print(f"\n🔴 ACCIONES REQUERIDAS:\n")
            for i, rec in enumerate(critical_recs, 1):
                print(f"{i}. {rec}")
        else:
            print(f"\n✓ No se requieren acciones inmediatas\n")
    
    def validate(self, device_names: List[str] = None) -> bool:
        """Orquesta flujo completo de validación"""
        try:
            if not self.load_testbed():
                return False
            
            devices, errors = self.connect_to_devices(device_names)
            
            if not devices:
                print(f"\n[ERROR] No fue posible conectar a dispositivos")
                return False
            
            all_results = {}
            for device_name, device in devices.items():
                results = self.validate_device(device)
                all_results[device_name] = results
                
                try:
                    device.disconnect()
                except:
                    pass
            
            self.results = all_results
            self.generate_summary_report(all_results)
            
            return True
            
        except KeyboardInterrupt:
            print(f"\n[WARN] Validación interrumpida")
            return False
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Punto de entrada principal"""
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║         LACP RESILIENCY VALIDATOR - Cisco Devices            ║
    ║      IOS/IOS-XE/NX-OS Port-Channel Analysis with pyATS       ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    TESTBED_FILE = "testbed.yaml"
    
    validator = LACPResiliencyValidator(TESTBED_FILE)
    
    try:
        success = validator.validate()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n[ERROR] Excepción: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
