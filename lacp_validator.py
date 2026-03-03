#!/usr/bin/env python3

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

PROTOCOLO_ESPERADO = "lacp"
PORT_CHANNEL_OBJETIVO = 1
TIEMPO_ESPERA_SEGUNDOS = 3
TESTBED_FILE = "testbed.yaml"


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
# FUNCIÓN: MOSTRAR MENÚ DE DISPOSITIVOS
# ============================================================================

def mostrar_menu_dispositivos(testbed_file: str) -> Optional[List[str]]:
    """Muestra menú para elegir dispositivos a validar"""
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
# FUNCIÓN: MENÚ DE SIMULACIÓN DE FALLO (NUEVA)
# ============================================================================

def mostrar_menu_simulacion() -> str:
    """
    Menú para que el usuario ELIJA si desea hacer la simulación de fallo.
    
    Retorna:
      "completa" - Hacer la simulación completa (10 pasos)
      "diagnostico" - Solo verificar estado (sin simulación)
      "cancelar" - Cancelar validación
    """
    
    imprimir_titulo("OPCIONES DE VALIDACIÓN")
    
    print(f"\n¿Qué deseas hacer?\n")
    print(f"  [1] VALIDACIÓN COMPLETA (Simular fallo y recuperación)")
    print(f"      └─ El script hará shutdown, validará resiliencia y recuperará")
    print(f"      └─ Duración: ~30 segundos")
    print(f"      └─ ADVERTENCIA: Causará breve desconexión")
    print(f"")
    print(f"  [2] DIAGNÓSTICO SOLAMENTE (Solo verificar estado)")
    print(f"      └─ Sin simular fallos")
    print(f"      └─ Verificar protocolo, redundancia, distribución")
    print(f"      └─ Duración: ~5 segundos")
    print(f"      └─ Seguro: Sin desconexiones")
    print(f"")
    print(f"  [3] CANCELAR")
    print(f"      └─ Salir sin validar")
    
    imprimir_pregunta("Elige una opción (1/2/3):")
    opcion = input("  → ").strip()
    
    if opcion == "1":
        imprimir_exito("Realizarás VALIDACIÓN COMPLETA")
        imprimir_advertencia("El Port-Channel tendrá una interfaz deshabilitada temporalmente")
        return "completa"
    elif opcion == "2":
        imprimir_exito("Realizarás DIAGNÓSTICO SOLAMENTE (sin simulación)")
        return "diagnostico"
    elif opcion == "3":
        imprimir_info("Cancelando validación")
        return "cancelar"
    else:
        imprimir_error("Opción no válida")
        return mostrar_menu_simulacion()  # Reintentar


# ============================================================================
# FUNCIÓN 1: CONECTAR
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
    
    if len(miembros_despues) == 0:
        imprimir_error("Port-Channel colapsó (0 miembros)")
        return False
    
    imprimir_exito(f"Port-Channel operacional ({len(miembros_despues)} miembro(s))")
    
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
    miembros_recuperados: int,
    modo_validacion: str
) -> bool:
    """Genera reporte visual final del test"""
    
    imprimir_titulo("REPORTE FINAL - TEST DE VALIDACIÓN")
    
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
    
    print(f"\n✅ REDUNDANCIA:")
    if miembros_antes >= 2:
        print(f"   ✓ TIENE REDUNDANCIA: {miembros_antes} interfaces bundled")
    else:
        print(f"   ✗ SIN REDUNDANCIA: Solo {miembros_antes} interfaz(ces)")
    
    if modo_validacion == "completa":
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
    
    if modo_validacion == "diagnostico":
        print(f"   MODO: Diagnóstico (sin simulación)")
        if protocolo_ok and miembros_antes >= 2:
            print(f"   ✓✓ ESTADO ACTUAL BUENO")
            print(f"   Protocolo: Correcto | Redundancia: OK")
            return True
        else:
            print(f"   ⚠ ESTADO ACTUAL CON PROBLEMAS")
            return False
    
    else:  # modo completa
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
# FUNCIÓN: VALIDAR UN DISPOSITIVO (MEJORADA)
# ============================================================================

def validar_dispositivo(nombre_dispositivo: str, modo_validacion: str) -> bool:
    """
    Ejecuta validación según el modo seleccionado.
    
    modo_validacion:
      "completa" - Simulación completa (10 pasos)
      "diagnostico" - Solo diagnóstico (sin simulación)
    """
    
    imprimir_titulo(f"VALIDANDO: {nombre_dispositivo}")
    
    print(f"\nConfiguración:")
    print(f"  - Dispositivo: {nombre_dispositivo}")
    print(f"  - Protocolo: {PROTOCOLO_ESPERADO.upper()}")
    print(f"  - Port-Channel: {PORT_CHANNEL_OBJETIVO}")
    print(f"  - Modo: {'VALIDACIÓN COMPLETA (con simulación)' if modo_validacion == 'completa' else 'DIAGNÓSTICO (sin simulación)'}")
    
    # Paso 1: Conectar
    imprimir_seccion("PASO 1: Conectar al Dispositivo")
    dispositivo = conectar_equipo(nombre_dispositivo, TESTBED_FILE)
    
    if dispositivo is None:
        imprimir_error("Conexión fallida")
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
    protocolo_ok, protocolo_detectado = verificar_protocolo(datos_pc, PROTOCOLO_ESPERADO)
    
    print(f"Esperado:  {PROTOCOLO_ESPERADO.upper()}")
    print(f"Detectado: {protocolo_detectado.upper()}")
    
    if not protocolo_ok:
        imprimir_error("PROTOCOLO INCORRECTO")
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
    
    # SI MODO DIAGNÓSTICO: Saltamos la simulación
    if modo_validacion == "diagnostico":
        imprimir_seccion("DIAGNÓSTICO COMPLETADO (Sin Simulación)")
        
        test_pasado = generar_reporte_final(
            nombre_dispositivo,
            PORT_CHANNEL_OBJETIVO,
            PROTOCOLO_ESPERADO,
            protocolo_detectado,
            "N/A",
            True,
            len(miembros_antes),
            len(miembros_antes),
            len(miembros_antes),
            "diagnostico"
        )
        
        imprimir_seccion("Limpiar")
        desconectar_equipo(dispositivo)
        
        return test_pasado
    
    # SI MODO COMPLETA: Continuamos con la simulación
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
        len(miembros_recuperados),
        "completa"
    )
    
    # Limpiar
    imprimir_seccion("Limpiar")
    desconectar_equipo(dispositivo)
    
    return test_pasado


# ============================================================================
# FUNCIÓN: VALIDAR MÚLTIPLES DISPOSITIVOS
# ============================================================================

def validar_multiples_dispositivos(dispositivos: List[str], modo_validacion: str) -> Dict[str, bool]:
    """Valida múltiples dispositivos"""
    
    resultados = {}
    total = len(dispositivos)
    
    for i, dispositivo in enumerate(dispositivos, 1):
        print(f"\n\n{'#'*70}")
        print(f"# DISPOSITIVO {i} DE {total}: {dispositivo}")
        print(f"{'#'*70}\n")
        
        resultado = validar_dispositivo(dispositivo, modo_validacion)
        resultados[dispositivo] = resultado
        
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
    """Punto de entrada: Menú interactivo"""
    
    imprimir_titulo("ETHERCHANNEL RESILIENCE SIMULATOR - v3.0")
    print("\n[INFO] Con menú para seleccionar tipo de validación")
    
    # Mostrar menú de dispositivos
    dispositivos_a_validar = mostrar_menu_dispositivos(TESTBED_FILE)
    
    if dispositivos_a_validar is None:
        imprimir_error("No se seleccionaron dispositivos")
        return False
    
    # Mostrar menú de tipo de validación
    modo_validacion = mostrar_menu_simulacion()
    
    if modo_validacion == "cancelar":
        imprimir_info("Validación cancelada")
        return False
    
    # Validar dispositivos
    if len(dispositivos_a_validar) == 1:
        # Un solo dispositivo
        resultado = validar_dispositivo(dispositivos_a_validar[0], modo_validacion)
        return resultado
    else:
        # Múltiples dispositivos
        resultados = validar_multiples_dispositivos(dispositivos_a_validar, modo_validacion)
        imprimir_resumen_final(resultados)
        
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
