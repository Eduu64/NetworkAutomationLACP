# LACP RESILIENCY VALIDATOR - Documentación Completa

## 📋 Descripción General

Script de automatización de redes para validar la resiliencia de agregaciones de enlaces LACP 
en dispositivos Cisco IOS/IOS-XE/NX-OS usando pyATS y Genie.

**Versión**: 1.0 | **Python**: 3.8+ | **Framework**: pyATS + Genie

---

## 🎯 Funcionalidades Principales

### 1. Recolección Estructurada de Datos
- Usa `device.learn('etherchannel')` para obtener información normalizada
- Compatible con IOS, IOS-XE y NX-OS (parsers automáticos de Genie)

### 2. Validación de Resiliencia

**Criterio 1: Redundancia Mínima**
- Requisito: Al menos 2 interfaces físicas en estado 'up' (bundled)
- Detecta Port-Channels con un solo miembro operacional
- Riesgo: Pérdida de conectividad si la interfaz única falla

**Criterio 2: Distribución de Hardware**
- Requisito: Miembros distribuidos en diferentes slots/tarjetas
- Detecta: Todos los miembros en el mismo módulo
- Riesgo: Punto único de fallo si se reinicia/falla un módulo
- Ejemplo: Gi1/0/1 + Gi1/0/5 = MISMO SLOT → Riesgo CRÍTICO

**Criterio 3: Protocolo LACP Activo**
- Requisito: Protocolo LACP en modo 'active' en todos los miembros
- Detecta: Protocolos estáticos (PAgP, Static) o LACP modo 'passive'
- Riesgo: Manejo incorrecto de fallas

### 3. Reportes Claros y Ejecutivos
- Estado individual de cada Port-Channel
- Resumen consolidado con estadísticas
- Identificación de Port-Channels en riesgo
- Recomendaciones accionables

---

## 📦 Estructura del Código

### Clases Principales

**ResiliencyStatus (Enum)**
- PASSED: ✓ Port-Channel cumple todos criterios
- FAILED: ✗ Port-Channel tiene problemas críticos
- WARNING: ⚠ Port-Channel tiene advertencias
- UNKNOWN: ? No se pudo validar

**PortChannelValidation (Dataclass)**
Almacena: device_name, port_channel, status, num_members_up, total_members, 
protocol_type, hardware_distributed, slots_used, findings, recommendations

**LACPResiliencyValidator (Clase Principal)**
- load_testbed(): Carga archivo YAML
- connect_to_devices(): Conecta a dispositivos con pyATS
- learn_etherchannel(): Ejecuta device.learn('etherchannel')
- parse_interface_slot(): Extrae slot del nombre de interfaz
- validate_portchannel(): Aplica criterios de resiliencia
- validate_device(): Valida todos los Port-Channels de un dispositivo
- validate(): Orquesta flujo completo

---

## 🔍 Cómo pyATS/Genie Parsea la Información

```
Dispositivo Cisco
    ↓
device.learn('etherchannel')
    ↓
pyATS detecta OS y selecciona parser de Genie
    ↓
Ejecuta: 'show etherchannel summary' (IOS/IOS-XE)
         'show port-channel summary' (NX-OS)
    ↓
Parsea salida con regex/templates específicos del SO
    ↓
Retorna DICT NORMALIZADO (idéntico en todos los OS)
```

### Estructura Normalizada Retornada

```python
{
    'interfaces': {
        'Port-channel1': {
            'protocol': 'lacp',
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
        }
    }
}
```

Esta estructura es **idéntica** en IOS, IOS-XE y NX-OS (abstraída automáticamente por Genie)

---

## 🚀 Instalación

### Dependencias

```bash
pip install pyats genie pyyaml
```

### Estructura de Directorios

```
project/
├── lacp_validator.py          # Script principal
├── testbed.yaml               # Configuración de dispositivos
└── LACP_README.md             # Esta documentación
```

### Configurar testbed.yaml

```yaml
devices:
  switch-core:
    type: switch
    os: iosxe                    # iosxe, ios, nxos
    platform: 'Catalyst 9300'
    connections:
      cli:
        protocol: ssh
        ip: 10.0.1.10
        port: 22
    credentials:
      default:
        username: admin
        password: password123
      enable:
        password: enable123
```

---

## 🔧 Uso

### Ejecución Básica

```bash
python lacp_validator.py
```

Valida todos los dispositivos en testbed.yaml

### Salida Esperada

```
PORT-CHANNEL1: ✓ PASSED
  ✓ Redundancia OK: 2/2 miembros up
  ✓ Distribución OK: 2 slot(s) [1, 2]
  ✓ LACP en modo active

PORT-CHANNEL2: ✗ FAILED
  ✗ Solo 1/3 miembro(s) up (mín: 2)
  📋 Recomendaciones:
     → Investigar Puerto-channel2: verificar LACP mode, cables, STP
```

---

## 📊 Interpretación de Resultados

### Estados

| Estado | Significado |
|--------|------------|
| ✓ PASSED | Port-Channel pasa todas las validaciones |
| ⚠ WARNING | Port-Channel tiene advertencias (no críticas) |
| ✗ FAILED | Port-Channel tiene problemas críticos |

### Casos de Riesgo Detectados

**1. Falta de Redundancia**
```
✗ Solo 1/2 miembro(s) up
```
- Causa: Interfaz no bundled (down, err-disabled)
- Solución: Revisar interfaz física, cable, configuración LACP

**2. Falta de Distribución**
```
✗ Todos los miembros en el mismo slot/chasis
```
- Causa: Interfaces en la misma tarjeta (Gi1/0/1 + Gi1/0/5)
- Solución: Distribuir entre tarjetas diferentes (Gi1/0/1 + Gi2/0/1)

**3. Protocolo No LACP**
```
✗ Protocolo: PAGP (no LACP)
```
- Causa: Agregación estática o PAgP
- Solución: Migrar a LACP para resiliencia dinámica

---

## 🛠️ Configuración Correcta (IOS-XE)

```
interface Port-channel1
 description Link to Distribution
 switchport mode trunk

interface GigabitEthernet1/0/1
 description Link to Dist-1
 channel-group 1 mode active

interface GigabitEthernet2/0/1
 description Link a Dist-1 (TARJETA DIFERENTE)
 channel-group 1 mode active
```

✓ 2 miembros | ✓ Modo active | ✓ Slots diferentes (1, 2)

---

## 📝 Personalización

### Cambiar Mínimo de Miembros

En `LACPResiliencyValidator`:
```python
self.MIN_REDUNDANT_MEMBERS = 3  # Cambiar a 3
```

### Cambiar Número Mínimo de Slots

```python
self.MIN_SLOTS_FOR_DISTRIBUTION = 3
```

---

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| ModuleNotFoundError: pyats | `pip install pyats genie --upgrade` |
| testbed not found | Verificar que testbed.yaml esté en dir actual |
| Connection timeout | Revisar IP, puerto SSH, conectividad |
| Port-Channels no encontrados | `show etherchannel summary` en dispositivo |

---

## 📚 Referencias

- Documentación Genie: https://pubhub.devnetcloud.com/media/genie-feature-browser/docs/
- pyATS Documentation: https://pubhub.devnetcloud.com/media/pyats/docs/

---

**Versión**: 1.0  

