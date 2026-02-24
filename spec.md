# Especificación de Requisitos de Software: ASPlayer

## 1. Entorno de Ejecución y Restricciones Generales

*   **Hardware Objetivo**: Raspberry Pi equipado con una pantalla táctil de 3.5 pulgadas.
*   **Lenguaje Base**: Python.
*   **Modo de Ventana**: Ejecución estricta en pantalla completa (Fullscreen) sin bordes ni decoraciones del sistema operativo.
*   **Persistencia**: El sistema debe contar con un mecanismo de serialización para Guardar y Abrir toda la configuración del workspace (estructura de nodos, valores de propiedades, conexiones de cables y ruteo de hardware) en un archivo local.

## 2. Lineamientos de UI/UX (Diseño e Interacción)

*   **Estética Visual**: Diseño ultra-minimalista basado en la imagen de referencia. Uso exclusivo de paletas monocromáticas (fondo claro o grisáceo, líneas finas oscuras).
*   **Iconografía**: Dibujos esquemáticos simples, construidos con líneas negras continuas (sin rellenos sólidos complejos).
*   **Adaptabilidad Táctil**: Debido al tamaño de la pantalla (3.5"), todos los elementos interactivos (botones, pines, sliders) deben tener un área de contacto grande y márgenes amplios ("hitboxes" extendidas) para evitar toques accidentales.
*   **Tipografía**: Fuentes sans-serif legibles y sobrias para toda la interfaz.

## 3. Distribución Espacial de la Interfaz

La pantalla se divide en varias zonas funcionales principales:

### 3.1. Barra Inferior Global (Always-on-top)
*   **Visibilidad**: Debe contener un área reservada y siempre visible.
*   **Control de Reproducción**: Un icono prominente de Play / Stop que controla la ejecución global del diagrama lógico actual.

### 3.2. Panel Izquierdo Retráctil (Configuración Global)
*   **Despliegue**: Se despliega de forma horizontal desde el borde izquierdo.
*   **Función**: Definir la cantidad total de "Canales de Salida" lógicos que el usuario desea usar en su diagrama.
*   **Validación de Hardware**: El sistema debe contrastar la cantidad de canales lógicos solicitados con las salidas físicas reales del dispositivo. Si la solicitud excede la capacidad física, debe lanzar una advertencia modal o toast minimalista (con opción de cierre/aceptación) indicando la discrepancia.

### 3.3. Panel Derecho Retráctil (Inspector de Propiedades)
*   **Despliegue**: Se despliega horizontalmente desde el borde derecho.
*   **Contenido**: Su contenido es dinámico y reactivo: se puebla con las propiedades específicas del nodo que el usuario tenga seleccionado (clicado) en el panel principal en ese momento.

### 3.4. Canvas Principal (Sistema de Nodos) - Flujo de Inicialización e Instanciación
*   **Estado Cero y Nodos Semilla**: Al iniciar un nuevo esquema o al abrir la aplicación por primera vez, el canvas no debe contener ninguna fuente de audio ni ningún trigger preexistente.
*   **Aparición Automática Exclusiva**: Los únicos nodos que el sistema instancia y renderiza automáticamente en el lienzo son los Nodos de Canal de Salida (situados en la capa extrema derecha). La cantidad exacta de estos nodos está estrictamente dictada por el número configurado por el usuario en el Panel Izquierdo retráctil.
*   **Creación Dinámica Interactiva (Flujo Hacia Atrás)**: La creación de cualquier nodo adicional en el canvas depende 100% de la interacción del usuario con los pines de entrada de los nodos ya existentes, siguiendo un orden estricto.
    *   **Generación de Fuentes**: El usuario hace clic en el pin de entrada de un Nodo de Canal. Solo entonces, el programa instancia un nuevo Nodo de Fuente de Audio en la capa central y traza automáticamente el cable de conexión entre ambos.
    *   **Generación de Triggers**: Una vez que existe un Nodo de Fuente, el usuario hace clic en el pin de entrada de este. El programa responde instanciando un nuevo Nodo Trigger en la capa izquierda y conectándolo a la fuente.
*   **Prevención de Nodos Huérfanos**: Este diseño asegura que ningún nodo de Fuente o Trigger pueda existir en el canvas sin estar explícitamente conectado a un nodo de nivel superior en la jerarquía, manteniendo el flujo del workspace siempre limpio y funcional.

## 4. Interacción con Conexiones (Cables)

*   **Direccionalidad**: Las conexiones van de izquierda a derecha (Trigger -> Fuente -> Canal).
*   **Múltiples Conexiones (1 a N)**: Un nodo de salida puede conectarse a múltiples pines de entrada. Ejemplo: Una única Fuente de Audio puede ramificarse (conectarse) a varios Canales de Salida simultáneamente.
*   **Gestión de Cables**: El usuario debe poder trazar nuevos conectores táctilmente entre un puerto de salida y un pin de entrada, así como eliminar cables existentes (mediante un gesto táctil prolongado, un botón de eliminar o tocando la línea del cable).

## 5. Definición de Nodos y sus Propiedades

### 5.1. Nodos de Canal de Salida (Output Channels - Capa Derecha)
*   **Creación**: Se instancian automáticamente según el número definido en el Panel Izquierdo.
*   **Representación Visual**: Una bocina simple trazada en líneas, un pequeño índice numérico (ej. 1, 2, 3...) y un pin de entrada ubicado a la izquierda del nodo.
*   **Estado Visual**: Si el canal físico asociado existe en el hardware, el nodo se muestra "vivo" (trazos fuertes/oscuros). Si está mapeado a un canal inexistente o en error, se muestra desactivado (líneas atenuadas/grises).
*   **Comportamiento del Pin de Entrada**: Al hacer clic en un pin de entrada vacío, el sistema auto-genera y conecta un nodo previo de la capa "Fuente de Audio".
*   **Propiedades (Mostradas en Panel Derecho al hacer clic)**: Nombre real del hardware subyacente que está utilizando; listas desplegables para seleccionar el dispositivo de hardware objetivo y los canales disponibles; y un selector para mapear la señal lógica del nodo específicamente al canal "Izquierdo" o "Derecho".

### 5.2. Nodos de Fuente de Audio (Audio Sources - Capa Central)
*   **Representación Visual**: Posee un pin de entrada (izquierdo) y un puerto de salida (derecho). El icono del nodo cambia dinámicamente según su tipo: "Onda de frecuencia" o "Archivo de audio".
*   **Comportamiento del Pin de Entrada**: Al hacer clic en su pin de entrada, se auto-genera y conecta un nodo previo de la capa "Trigger".
*   **Propiedades Comunes**: Lista desplegable principal en el Panel Derecho para alternar la naturaleza del nodo entre Onda o Archivo.
*   **Propiedades Específicas (Modo Onda)**: Selector de tipo de forma de onda (senoidal, cuadrada, etc.); control para la Frecuencia (Hz); y opciones de temporalidad ("Infinita", "Tiempo Predeterminado", o modo "Intermitente" con intervalos definibles).
*   **Propiedades Específicas (Modo Archivo de Audio)**: Navegador de directorios para seleccionar archivos locales; control de segmento con slider de doble manija para delimitar inicio y fin; visualización de reproducción con barra de progreso interactiva (seek); control de bucle (loop infinito o "N" veces); y control de silencios (padding) antes, después o al completar el loop total.

### 5.3. Nodos Trigger (Disparadores - Capa Izquierda)
*   **Representación Visual**: Un icono de interruptor (switch) simple. Posee un puerto de salida (derecho) pero no pines de entrada lógicos.
*   **Propiedades (Mostradas en Panel Derecho al hacer clic)**: Lista desplegable para Tipo de Trigger y un botón de Disparador Manual para forzar la ejecución del trigger artificialmente y probar el flujo.
*   **Nota Arquitectónica**: Actualmente solo existirá el trigger "Inicio del Programa" (On Start), pero el código interno debe utilizar un patrón de diseño abstracto (ej. Strategy u Observer) para que la adición de futuros triggers (ej. GPIO input, temporizador, evento de red) sea modular y no afecte el core.
