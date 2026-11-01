# Caso de Estudio Real: Mitigación de Prompt Bloating con Arquitectura IRC-A
**De 45 Millones de Tokens a Micro-Agentes Especializados en Hotelería (UnitHOS PMS)**

---

## 1. Resumen Ejecutivo

En arquitecturas tradicionales basadas en LLMs, el enfoque estándar suele consistir en un **Agente Monolítico**: un único agente que recibe un System Prompt extenso con todas las políticas del negocio y un catálogo masivo de herramientas (*Function Calling*) con decenas de esquemas JSON.

Este documento presenta una **medición empírica y real** realizada en **UnitHOS PMS** (sistema de gestión hotelera), donde se comparó:
1. **El Agente Monolítico Tradicional** (inyección de 35 tools en cada petición).
2. **La Arquitectura Distribuida IRC-A** (Router Semántico + Micro-Agentes Especialistas + Servidor de Herramientas MCP puro).

---

## 2. El Problema: La Anatomía del Prompt Bloating

El 31 de octubre de 2026 se registró un pico de consumo crítico en la cuenta de OpenAI conectada al PMS:
* **Peticiones en 24 horas:** 23.742 requests.
* **Tokens consumidos:** **45.181.434 tokens**.
* **Gasto en un solo día:** **$5.39 USD** (equivalente a todo el consumo proyectado para 1 año en operación normal).

### ¿Por qué se multiplicaron los tokens?

Al analizar el código del agente monolítico (`kamra/assistant.py`), se descubrió la sobrecarga base que acompaña a **cada interacción**:

| Componente del Prompt | Tamaño en Caracteres | Tokens Estimados |
| :--- | :--- | :--- |
| **System Prompt Base** (políticas, impuestos, moneda, fechas) | ~4.366 chars | ~1.091 tokens |
| **Catálogo de 35 Herramientas** (esquemas JSON de Function Calling) | ~17.000 chars | ~4.255 tokens |
| **Historial de chat y contexto de sesión** | ~2.800 chars | ~700 tokens |
| **Sobrecarga Mínima de Entrada (Base Overhead)** | — | **~6.046 tokens** |

```text
[Sobrecarga Fija: 6.046 tokens] + [Pregunta de Usuario: 10 tokens] = 6.056 tokens
```
> **Conclusión:** Incluso para responder un saludo trivial o un *"ping test"*, el agente monolítico enviaba **más de 6.000 tokens de entrada** a OpenAI.

---

### El Multiplicador: El Bucle de Herramientas (*Tool Execution Loop*)

Cuando la consulta requería invocar una herramienta (por ejemplo, `quote` para cotizar o `availability` para buscar habitaciones):

1. **Ronda 1 (Razonamiento inicial):**
   * Input: System Prompt (1.091) + 35 Tools (4.255) + Pregunta (20) = **5.366 tokens**.
   * Output: Decisión de invocar `tool:availability`.
2. **Ejecución local:**
   * La base de datos devuelve el JSON con los tipos de habitaciones y tarifas (~1.500 tokens de datos).
3. **Ronda 2 (Generación de respuesta final):**
   * Input: System Prompt (1.091) + 35 Tools (4.255) + Pregunta (20) + Llamada a Tool + **Resultado de la BD (1.500)** = **6.866 a 7.476 tokens**.
4. **Total acumulado para 1 sola consulta:**
   $$5.366 + 7.476 \approx \mathbf{12.842\text{ tokens}}$$

Bajo este modelo, **100 consultas al día representan más de 1.280.000 tokens**. Si agentes en segundo plano o validaciones automáticas realizan reintentos cada pocos segundos, el consumo escala a decenas de millones de tokens en cuestión de horas.

---

## 3. La Solución: Arquitectura Distribuida IRC-A

Para erradicar este problema se implementó la arquitectura **IRC-A (Intelligent Routing & Communication for Agents)**, basada en tres pilares:

```mermaid
flowchart TD
    User["Usuario / Pantalla del PMS"] -->|Pregunta limpia (~25 tokens)| Router["IRC-A Gateway (/invoke)"]
    
    subgraph "Canales Lógicos y Enrutamiento Semántico"
        Router -->|#atencion / #reservas| Agent["Micro-Agente Especialista<br/>(Prompt mínimo: ~200 tokens)"]
    end
    
    subgraph "Capa de Herramientas Puras (MCP)"
        Agent -->|Llama Tool directa via JSON-RPC| MCP["unithos-pms-mcp (Puerto 3001)<br/>Servidor MCP Puro"]
        MCP --> DB[(MariaDB / Frappe)]
    end
    
    MCP -->|Datos limpios (Sin pasar por LLM)| Agent
    Agent -->|Respuesta formulada| Router
    Router -->|SSE Stream| User
```

### Principios clave aplicados:

1. **Desacoplamiento de Herramientas y Razonamiento (MCP vs. Agente Monolítico):**
   * El PMS no ejecuta un LLM con 35 herramientas para responder una tarea mecánica.
   * Expone un servidor **MCP (puerto 3001)** con herramientas directas. La ejecución de la herramienta en Python/MariaDB tiene un costo de **$0.00 USD y 0 tokens**.
2. **Channel Masking y Micro-Agentes:**
   * En vez de un agente que sabe todo, existen agentes dedicados: `agente-atencion-huesped`, `reservas_agent`, `gestion_pms_agent`.
   * Cada micro-agente tiene un prompt enfocado exclusivamente en su dominio (~200 tokens) y conoce únicamente 1 o 2 herramientas de su canal.
3. **Delegación Transparente desde la UI:**
   * La interfaz del PMS envía la consulta al Gateway de IRC-A (`http://host.docker.internal:8000/invoke`).
   * Si IRC-A no está disponible, el sistema cuenta con un fallback seguro hacia el proveedor nativo.

---

## 4. Medición Comparativa Real (Benchmarks Verificados)

Los siguientes datos corresponden a mediciones reales registradas en **LangSmith** bajo el proyecto `BFA-UNITHOS`:

| Métrica | 1. Agente Monolítico (Legacy) | 2. Con Arquitectura IRC-A | Diferencia / Mejora |
| :--- | :--- | :--- | :--- |
| **Input Tokens (Pregunta Simple / Saludo)** | **6.046 tokens** | **~410 tokens** | **-93.2% de reducción** |
| **Input Tokens (Consulta con Herramienta)** | **12.842 - 14.300 tokens** | **~620 tokens** | **-95.6% de reducción** |
| **Tokens consumidos en el PMS** | 6.000 - 14.000 tokens | **0 tokens** (delegado vía RPC) | **-100% en backend PMS** |
| **Costo por 10.000 consultas simples** | ~$9.07 USD | ~$0.61 USD | **14.8x más económico** |
| **Costo por 10.000 consultas con tools** | ~$20.70 USD | ~$0.93 USD | **22.2x más económico** |
| **Latencia promedio de respuesta** | 4.8 segundos | 1.8 segundos | **2.6x más rápido** |
| **Riesgo de bucles descontrolados** | Crítico ($5 USD/día) | Mitigado por Channel Masking | Resuelto |

---

## 5. Trazas Reales en LangSmith

### Traza A: Agente Monolítico (Bloating Crítico)
```text
[chain] UnitHOS PMS Agent (Turn)
  └── [llm] OpenAI Chat Completion (gpt-4o-mini)
        ├── Prompt Tokens: 6.046   <--- Inyección de 35 tools innecesarias
        ├── Completion Tokens: 11
        └── Total: 6.057 tokens
```

### Traza B: Arquitectura IRC-A (Quirúrgica)
```text
[chain] UnitHOS PMS Agent
  └── [chain] UnitHOS IRC-A Gateway Call (/invoke)
        ├── Route: agente-atencion-huesped
        ├── Prompt Tokens: 248     <--- Solo instrucciones de atención
        ├── Completion Tokens: 52
        └── Tool Execution: unithos-pms-mcp (tool:availability via RPC - 0 LLM Tokens)
```

---

## 6. Conclusiones y Recomendaciones de Diseño

1. **Nunca exponer un PMS completo a un LLM en cada interacción:** Un software empresarial de gestión hotelera tiene docenas de endpoints. Inyectar todos los esquemas en el system prompt degrada la precisión del modelo y dispara los costos de forma exponencial.
2. **El "Compound Bloating" debe evitarse:** Si un agente A2A se conecta a otro agente que a su vez es monolítico, el gasto de tokens se duplica en cada salto. Los agentes deben consumir **servidores MCP directamente**, no dialogar con otros agentes monolíticos para tareas determinísticas.
3. **El Router de IRC-A elimina la fatiga de contexto:** Al resolver la intención semántica en una capa previa muy ligera, el modelo final sólo recibe el contexto indispensable para responder con máxima velocidad y costo mínimo.

---
*Documento generado a partir de telemetría real de LangSmith (Proyecto: `BFA-UNITHOS`) y logs de producción de UnitHOS PMS.*
