#!/usr/bin/env python3
"""
  1. Conectarse a un dispositivo Cisco
  2. Obtener la configuración de EtherChannels
  3. Simular una caída de interfaz (shutdown)
  4. Validar que el Puerto-Channel mantiene disponibilidad
  5. Recuperar la interfaz y confirmar reintegración
"""

import time
import sys
from typing import Dict, List, Tuple, Optional

try:
    from pyats.topology import loader
except ImportError:
    print("[ERROR] pip install pyats genie")
    sys.exit(1)


# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================

PROTOCOLO_ESPERADO = "lacp"            # "lacp" o "pagp"
PORT_CHANNEL_OBJETIVO = 1              # Número del Port-Channel
TIEMPO_ESPERA_SEGUNDOS = 3             # Segundos entre acciones
TESTBED_FILE = "testbed.yaml"          # Ruta al archivo testbed


# ============================================================================
# FUNCIONES DE IMPRESIÓN
# ============================================================================

def imprimir_titulo(texto):
    """Imprime un título decorado"""
    print(f"\n{'='*70}")
    print(f"  {texto}")
    print(f"{'='*70}")


def imprimir_seccion(texto):
    """Imprime una sección"""
    print(f"\n[SECCIÓN] {texto}")
    print(f"{'-'*70}")


def imprimir_exito(texto):
    """Mensaje de éxito"""
    print(f"[✓ OK] {texto}")


def imprimir_error(texto):
    """Mensaje de error"""
    print(f"[✗ ERROR] {texto}")


def imprimir_info(texto):
    """Mensaje informativo"""
    print(f"[INFO] {texto}")


def imprimir_advertencia(texto):
    """Mensaje de advertencia"""
    print(f"[⚠ ADVERTENCIA] {texto}")


def imprimir_pregunta(texto):
    """Mensaje de pregunta"""
    print(f"\n[?] {texto}")


def esperar_segundos(segundos):
    """Espera N segundos"""
    print(f"\n⏳ Esperando {segundos} segundos...")
    for i in range(segundos, 0, -1):
        print(f"   {i}...", end=" ", flush=True)
        time.sleep(1)
    print("\n")


# ============================================================================
# FUNCIÓN: MOSTRAR MENÚ INTERACTIVO
# ============================================================================

def mostrar_menu_dispositivos(testbed_file: str) -> Optional[List[str]]:
    """
    Muestra un menú interactivo para elegir dispositivos.
    
    Opciones:
      1. Validar un dispositivo específico
      2. Validar todos los dispositivos
      3. Salir
    
    Retorna:
      Lista de dispositivos a validar, o None si el usuario cancela
    """
    try:
        imprimir_info(f"Cargando testbed desde: {testbed_file}")
        topologia = loader.load(testbed_file)
        dispositivos_disponibles = list(topologia.devices.keys())
        
        if not dispositivos_disponibles:
            imprimir_error("No hay dispositivos en el testbed")
            return None
        
        imprimir_titulo("SELECCIONAR DISPOSITIVOS PARA VALIDAR")
        
        print(f"\nDispositivos disponibles en {testbed_file}:")
        for i, dispositivo in enumerate(dispositivos_disponibles, 1):
            print(f"  {i}. {dispositivo}")
        
        print(f"\nOpciones:")
        print(f"  [A] Validar un dispositivo específico")
        print(f"  [B] Validar TODOS los dispositivos")
        print(f"  [S] Salir")
        
        imprimir_pregunta("Elige una opción (A/B/S):")
        opcion = input("  → ").strip().upper()
        
        if opcion == "S":
            imprimir_info("Saliendo...")
            return None
        
        elif opcion == "A":
            print(f"\nDispositivos disponibles:")
            for i, dispositivo in enumerate(dispositivos_disponibles, 1):
                print(f"  {i}. {dispositivo}")
            
            imprimir_pregunta("Ingresa el número del dispositivo (1-{})".format(
                len(dispositivos_disponibles)
            ))
            
            try:
                numero = int(input("  → "))
                if 1 <= numero <= len(dispositivos_disponibles):
                    dispositivo_seleccionado = dispositivos_disponibles[numero - 1]
                    imprimir_exito(f"Seleccionado: {dispositivo_seleccionado}")
                    return [dispositivo_seleccionado]
                else:
                    imprimir_error("Número fuera de rango")
                    return None
            except ValueError:
                imprimir_error("Debes ingresar un número")
                return None
        
        elif opcion == "B":
            imprimir_exito(f"Validando TODOS los dispositivos: {dispositivos_disponibles}")
            return dispositivos_disponibles
        
        else:
            imprimir_error("Opción no válida")
            return None
    
    except Exception as error:
        imprimir_error(f"Error al cargar testbed: {error}")
        return None


# ============================================================================
# FUNCIÓN 1: CONECTAR AL DISPOSITIVO
# ============================================================================

def conectar_equipo(nombre_dispositivo: str, testbed_file: str):
    """Conecta a un dispositivo usando pyATS"""
    try:
        topologia = loader.load(testbed_file)
        dispositivo = topologia.devices[nombre_dispositivo]
        
        imprimir_info(f"Conectando a {nombre_dispositivo}...")
        dispositivo.connect(log_stdout=False)
        
        imprimir_exito(f"Conectado a {nombre_dispositivo}")
        return dispositivo
        
    except KeyError:
        imprimir_error(f"Dispositivo '{nombre_dispositivo}' no en testbed")
        return None
        
    except Exception as error:
        imprimir_error(f"Error de conexión: {error}")
        return None


# ============================================================================
# FUNCIÓN 2: APRENDER ETHERCHANNEL
# ============================================================================

def aprender_etherchannel(dispositivo):
    """Obtiene información de EtherChannel usando Genie"""
    try:
        imprimir_info("Aprendiendo estado de EtherChannels...")
        datos = dispositivo.learn('etherchannel')
        imprimir_exito("Datos obtenidos")
        return datos
        
    except Exception as error:
        imprimir_error(f"No se pudo aprender etherchannel: {error}")
        return {}


# ============================================================================
# FUNCIÓN 3: EXTRAER PORT-CHANNEL
# ============================================================================

def extraer_info_portchannel(datos_etherchannel: Dict, numero_pc: int) -> Optional[Dict]:
    """Extrae información de un Port-Channel específico"""
    if not datos_etherchannel or 'interfaces' not in datos_etherchannel:
        return None
    
    interfaces = datos_etherchannel['interfaces']
    
    # Buscar formato IOS-XE (capitalizado)
    nombre_pc = f"Port-channel{numero_pc}"
    if nombre_pc in interfaces:
        return interfaces[nombre_pc]
    
    # Buscar formato NX-OS (minúscula)
    nombre_pc = f"port-channel{numero_pc}"
    if nombre_pc in interfaces:
        return interfaces[nombre_pc]
    
    return None


# ============================================================================
# FUNCIÓN 4: OBTENER MIEMBROS ACTIVOS
# ============================================================================

def obtener_miembros_activos(datos_pc: Dict) -> List[str]:
    """Obtiene interfaces que están bundled (activas)"""
    miembros_activos = []
    
    if not datos_pc or 'members' not in datos_pc:
        return miembros_activos
    
    for nombre_iface, estado in datos_pc['members'].items():
        if estado.get('bundled', False):
            miembros_activos.append(nombre_iface)
    
    return miembros_activos


# ============================================================================
# FUNCIÓN 5: VERIFICAR PROTOCOLO
# ============================================================================

def verificar_protocolo(datos_pc: Dict, protocolo_esperado: str) -> Tuple[bool, str]:
    """Verifica si el Port-Channel usa el protocolo esperado"""
    if not datos_pc:
        return False, "desconocido"
    
    protocolo_detectado = datos_pc.get('protocol', 'desconocido').lower()
    es_correcto = protocolo_detectado == protocolo_esperado.lower()
    
    return es_correcto, protocolo_detectado


# ============================================================================
# FUNCIÓN 6: SIMULAR FALLO
# ============================================================================

def simular_fallo(dispositivo, interfaz: str) -> bool:
    """Ejecuta shutdown en una interfaz"""
    try:
        imprimir_info(f"Ejecutando shutdown en {interfaz}...")
        
        comandos = [
            f"interface {interfaz}",
            "shutdown"
        ]
        
        dispositivo.configure(comandos)
        imprimir_exito(f"Interfaz {interfaz} deshabilitada")
        return True
        
    except Exception as error:
        imprimir_error(f"No se pudo ejecutar shutdown: {error}")
        return False


# ============================================================================
# FUNCIÓN 7: RECUPERAR INTERFAZ
# ============================================================================

def recuperar_interfaz(dispositivo, interfaz: str) -> bool:
    """Ejecuta no shutdown para rehabilitar la interfaz"""
    try:
        imprimir_info(f"Ejecutando no shutdown en {interfaz}...")
        
        comandos = [
            f"interface {interfaz}",
            "no shutdown"
        ]
        
        dispositivo.configure(comandos)
        imprimir_exito(f"Interfaz {interfaz} habilitada")
        return True
        
    except Exception as error:
        imprimir_error(f"No se pudo ejecutar no shutdown: {error}")
        return False


# ============================================================================
# FUNCIÓN 8: VALIDAR RESILIENCIA
# ============================================================================

def validar_resiliencia(
    miembros_antes: List[str],
    miembros_despues: List[str],
    interfaz_deshabilitada: str
) -> bool:
    """Valida si el Port-Channel mantiene resiliencia"""
    
    imprimir_seccion("Análisis de Resiliencia")
    
    print(f"Miembros ANTES:  {len(miembros_antes)} → {miembros_antes}")
    print(f"Miembros DESPUÉS: {len(miembros_despues)} → {miembros_despues}")
    
    # Verificar si hay miembros restantes
    if len(miembros_despues) == 0:
        imprimir_error("Port-Channel colapsó (0 miembros)")
        return False
    
    imprimir_exito(f"Port-Channel operacional ({len(miembros_despues)} miembro(s))")
    
    # Verificar que interfaz fue removida
    if interfaz_deshabilitada in miembros_despues:
        imprimir_advertencia("Interfaz aún en lista (puede tardar)")
    else:
        imprimir_exito("Interfaz removida correctamente")
    
    return True


# ============================================================================
# FUNCIÓN 9: GENERAR REPORTE
# ============================================================================

def generar_reporte_final(
    dispositivo_nombre: str,
    numero_pc: int,
    protocolo_esperado: str,
    protocolo_detectado: str,
    interfaz_testeada: str,
    resiliencia_ok: bool,
    miembros_antes: int,
    miembros_con_fallo: int,
    miembros_recuperados: int
) -> bool:
    """Genera reporte visual final del test"""
    
    imprimir_titulo("REPORTE FINAL - TEST DE RESILIENCIA")
    
    print(f"\n📋 DISPOSITIVO:")
    print(f"   Nombre: {dispositivo_nombre}")
    print(f"   Port-Channel: {numero_pc}")
    
    print(f"\n🔧 VALIDACIÓN DE PROTOCOLO:")
    protocolo_ok = protocolo_detectado.upper() == protocolo_esperado.upper()
    
    if protocolo_ok:
        print(f"   Esperado:  {protocolo_esperado.upper()}")
        print(f"   Detectado: {protocolo_detectado.upper()}")
        print(f"   ✓ PROTOCOLO CORRECTO")
    else:
        print(f"   Esperado:  {protocolo_esperado.upper()}")
        print(f"   Detectado: {protocolo_detectado.upper()}")
        print(f"   ✗ PROTOCOLO INCORRECTO")
    
    print(f"\n⚡ SIMULACIÓN DE FALLO:")
    print(f"   Interfaz testeada: {interfaz_testeada}")
    print(f"   Miembros antes:     {miembros_antes}")
    print(f"   Miembros con fallo: {miembros_con_fallo}")
    print(f"   Miembros recuperados: {miembros_recuperados}")
    
    print(f"\n🛡️  RESILIENCIA:")
    if resiliencia_ok:
        print(f"   ✓ Port-Channel SOBREVIVIÓ al fallo (RESILIENTE)")
        print(f"   ✓ Tráfico mantenido a través de otros miembros")
    else:
        print(f"   ✗ Port-Channel COLAPSÓ (NO RESILIENTE)")
        print(f"   ✗ Pérdida de conectividad")
    
    print(f"\n📊 CONCLUSIÓN:")
    
    if protocolo_ok and resiliencia_ok:
        print(f"   ✓✓✓ TEST PASADO: Protocolo OK + Resiliencia OK")
        return True
    elif protocolo_ok and not resiliencia_ok:
        print(f"   ⚠ TEST PARCIAL: Protocolo OK pero Resiliencia comprometida")
        return False
    else:
        print(f"   ✗✗✗ TEST FALLIDO: Protocolo incorrecto")
        return False


# ============================================================================
# FUNCIÓN 10: DESCONECTAR
# ============================================================================

def desconectar_equipo(dispositivo):
    """Cierra la conexión SSH"""
    try:
        dispositivo.disconnect()
        imprimir_exito("Conexión cerrada")
    except Exception as error:
        imprimir_advertencia(f"Error al desconectar: {error}")


# ============================================================================
# FUNCIÓN PRINCIPAL: VALIDAR UN DISPOSITIVO
# ============================================================================

def validar_dispositivo(nombre_dispositivo: str) -> bool:
    """
    Ejecuta la validación completa para UN dispositivo.
    
    Retorna: True si test pasó, False si falló o no se pudo ejecutar
    """
    
    imprimir_titulo(f"VALIDANDO: {nombre_dispositivo}")
    
    print(f"\nConfiguración:")
    print(f"  - Dispositivo: {nombre_dispositivo}")
    print(f"  - Protocolo: {PROTOCOLO_ESPERADO.upper()}")
    print(f"  - Port-Channel: {PORT_CHANNEL_OBJETIVO}")
    
    # Paso 1: Conectar
    imprimir_seccion("PASO 1: Conectar al Dispositivo")
    dispositivo = conectar_equipo(nombre_dispositivo, TESTBED_FILE)
    
    if dispositivo is None:
        imprimir_error("Conexión fallida - saltando este dispositivo")
        return False
    
    # Paso 2: Aprender estado inicial
    imprimir_seccion("PASO 2: Aprender Estado Inicial")
    datos_etherchannel = aprender_etherchannel(dispositivo)
    
    if not datos_etherchannel:
        imprimir_error("No se obtuvieron datos")
        desconectar_equipo(dispositivo)
        return False
    
    # Paso 3: Extraer Port-Channel
    imprimir_seccion(f"PASO 3: Extraer Port-Channel {PORT_CHANNEL_OBJETIVO}")
    datos_pc = extraer_info_portchannel(datos_etherchannel, PORT_CHANNEL_OBJETIVO)
    
    if datos_pc is None:
        imprimir_error(f"Port-Channel {PORT_CHANNEL_OBJETIVO} no encontrado")
        desconectar_equipo(dispositivo)
        return False
    
    imprimir_exito(f"Port-Channel {PORT_CHANNEL_OBJETIVO} encontrado")
    
    # Paso 4: Verificar protocolo
    imprimir_seccion("PASO 4: Verificar Protocolo")
    protocolo_ok, protocolo_detectado = verificar_protocolo(
        datos_pc,
        PROTOCOLO_ESPERADO
    )
    
    print(f"Esperado:  {PROTOCOLO_ESPERADO.upper()}")
    print(f"Detectado: {protocolo_detectado.upper()}")
    
    if not protocolo_ok:
        imprimir_error("PROTOCOLO INCORRECTO - Script finaliza para este dispositivo")
        desconectar_equipo(dispositivo)
        return False
    
    imprimir_exito("Protocolo correcto")
    
    # Paso 5: Listar miembros
    imprimir_seccion("PASO 5: Listar Miembros Activos")
    miembros_antes = obtener_miembros_activos(datos_pc)
    
    print(f"Miembros: {len(miembros_antes)}")
    for miembro in miembros_antes:
        print(f"  • {miembro}")
    
    if len(miembros_antes) < 1:
        imprimir_error("No hay miembros para probar")
        desconectar_equipo(dispositivo)
        return False
    
    interfaz_a_fallar = miembros_antes[0]
    
    # Paso 6: Simular fallo
    imprimir_seccion("PASO 6: Simular Fallo (Shutdown)")
    fallo_ok = simular_fallo(dispositivo, interfaz_a_fallar)
    
    if not fallo_ok:
        desconectar_equipo(dispositivo)
        return False
    
    esperar_segundos(TIEMPO_ESPERA_SEGUNDOS)
    
    # Paso 7: Aprender con fallo
    imprimir_seccion("PASO 7: Verificar Estado Después del Fallo")
    datos_etherchannel_fallo = aprender_etherchannel(dispositivo)
    datos_pc_fallo = extraer_info_portchannel(datos_etherchannel_fallo, PORT_CHANNEL_OBJETIVO)
    miembros_despues_fallo = obtener_miembros_activos(datos_pc_fallo)
    
    # Paso 8: Validar resiliencia
    imprimir_seccion("PASO 8: Validar Resiliencia")
    resiliencia_ok = validar_resiliencia(
        miembros_antes,
        miembros_despues_fallo,
        interfaz_a_fallar
    )
    
    # Paso 9: Recuperar
    imprimir_seccion("PASO 9: Recuperar Interfaz (No Shutdown)")
    recuperacion_ok = recuperar_interfaz(dispositivo, interfaz_a_fallar)
    
    esperar_segundos(TIEMPO_ESPERA_SEGUNDOS)
    
    # Paso 10: Verificar reintegración
    imprimir_seccion("PASO 10: Verificar Reintegración")
    datos_etherchannel_recuperado = aprender_etherchannel(dispositivo)
    datos_pc_recuperado = extraer_info_portchannel(
        datos_etherchannel_recuperado,
        PORT_CHANNEL_OBJETIVO
    )
    miembros_recuperados = obtener_miembros_activos(datos_pc_recuperado)
    
    print(f"Miembros recuperados: {len(miembros_recuperados)}")
    for miembro in miembros_recuperados:
        print(f"  • {miembro}")
    
    if len(miembros_recuperados) == len(miembros_antes):
        imprimir_exito("Interfaz reintegrada correctamente")
    else:
        imprimir_advertencia("Reintegración aún en progreso")
    
    # Paso 11: Reporte final
    test_pasado = generar_reporte_final(
        nombre_dispositivo,
        PORT_CHANNEL_OBJETIVO,
        PROTOCOLO_ESPERADO,
        protocolo_detectado,
        interfaz_a_fallar,
        resiliencia_ok,
        len(miembros_antes),
        len(miembros_despues_fallo),
        len(miembros_recuperados)
    )
    
    # Limpiar
    imprimir_seccion("Limpiar")
    desconectar_equipo(dispositivo)
    
    return test_pasado


# ============================================================================
# FUNCIÓN PRINCIPAL: VALIDAR MÚLTIPLES DISPOSITIVOS
# ============================================================================

def validar_multiples_dispositivos(dispositivos: List[str]) -> Dict[str, bool]:
    """
    Valida múltiples dispositivos y retorna resumen.
    
    Retorna: Diccionario con {dispositivo: test_pasado}
    """
    
    resultados = {}
    total = len(dispositivos)
    
    for i, dispositivo in enumerate(dispositivos, 1):
        print(f"\n\n{'#'*70}")
        print(f"# DISPOSITIVO {i} DE {total}: {dispositivo}")
        print(f"{'#'*70}\n")
        
        resultado = validar_dispositivo(dispositivo)
        resultados[dispositivo] = resultado
        
        # Pequeña pausa entre dispositivos
        if i < total:
            esperar_segundos(2)
    
    return resultados


# ============================================================================
# FUNCIÓN: RESUMEN FINAL MULTI-DISPOSITIVO
# ============================================================================

def imprimir_resumen_final(resultados: Dict[str, bool]):
    """Imprime resumen de validaciones de múltiples dispositivos"""
    
    imprimir_titulo("RESUMEN FINAL - VALIDACIÓN DE TODOS LOS DISPOSITIVOS")
    
    total = len(resultados)
    pasados = sum(1 for v in resultados.values() if v)
    fallidos = total - pasados
    
    print(f"\nResultados:")
    print(f"  Total dispositivos: {total}")
    print(f"  ✓ Tests PASADOS:    {pasados}")
    print(f"  ✗ Tests FALLIDOS:   {fallidos}")
    
    print(f"\nDetalle por dispositivo:")
    for dispositivo, resultado in resultados.items():
        if resultado:
            print(f"  ✓ {dispositivo:<30} PASADO")
        else:
            print(f"  ✗ {dispositivo:<30} FALLIDO")
    
    if fallidos == 0:
        print(f"\n✓✓✓ TODAS LAS VALIDACIONES PASARON")
    elif pasados > 0:
        print(f"\n⚠ VALIDACIÓN PARCIAL: {pasados} de {total} pasaron")
    else:
        print(f"\n✗✗✗ TODAS LAS VALIDACIONES FALLARON")


# ============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ============================================================================

def main():
    """Punto de entrada: Menú interactivo para elegir validación"""
    
    imprimir_titulo("ETHERCHANNEL RESILIENCE SIMULATOR - Versión Mejorada")
    
    # Mostrar menú y obtener dispositivos a validar
    dispositivos_a_validar = mostrar_menu_dispositivos(TESTBED_FILE)
    
    if dispositivos_a_validar is None:
        imprimir_error("No se seleccionaron dispositivos")
        return False
    
    # Validar dispositivos
    if len(dispositivos_a_validar) == 1:
        # Validar un solo dispositivo
        resultado = validar_dispositivo(dispositivos_a_validar[0])
        return resultado
    else:
        # Validar múltiples dispositivos
        resultados = validar_multiples_dispositivos(dispositivos_a_validar)
        imprimir_resumen_final(resultados)
        
        # Retornar True si al menos uno pasó
        return any(resultados.values())


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    try:
        resultado = main()
        
        if resultado:
            imprimir_exito("Validación(es) completada(s) exitosamente")
            sys.exit(0)
        else:
            imprimir_error("Validación(es) completada(s) con advertencias/errores")
            sys.exit(1)
            
    except KeyboardInterrupt:
        imprimir_advertencia("Validación interrumpida por usuario")
        sys.exit(2)
        
    except Exception as error:
        imprimir_error(f"Excepción: {error}")
        import traceback
        traceback.print_exc()
        sys.exit(3)
