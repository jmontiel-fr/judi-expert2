# Requirements Document

## Introduction

Ajustement dynamique des paramètres LLM en fonction du matériel détecté sur le poste de l'expert. Actuellement, les paramètres LLM (CTX_MAX, modèle, nombre de chunks RAG) sont fixés en dur pour tous les postes. Cette fonctionnalité détecte automatiquement les capacités matérielles au démarrage et adapte la configuration LLM pour optimiser les performances et la stabilité selon le profil du poste.

## Glossary

- **Hardware_Detector**: Service backend responsable de la détection des caractéristiques matérielles du poste (CPU, RAM, GPU)
- **Performance_Profile**: Ensemble de paramètres LLM pré-définis associé à une catégorie de matériel (modèle, CTX_MAX, chunks RAG, vitesse estimée)
- **Profile_Selector**: Composant qui associe les caractéristiques matérielles détectées au Performance_Profile approprié
- **Performance_Page**: Page de l'interface frontend affichant la configuration matérielle détectée, le profil sélectionné, et la table de référence des profils
- **LLM_Service**: Service backend existant qui gère les appels au LLM Ollama avec les paramètres de contexte et de modèle
- **Hardware_Info**: Structure de données contenant les informations matérielles détectées (type CPU, fréquence, cœurs, RAM totale, GPU)
- **Manual_Override**: Fonctionnalité permettant à l'expert de forcer un profil différent de celui détecté automatiquement
- **Step_Duration_Estimate**: Estimation de la durée de traitement LLM pour chaque étape du workflow (Step 1 à 5) selon le profil actif

## Requirements

### Requirement 1: Détection matérielle au démarrage

**User Story:** As an expert, I want the system to automatically detect my hardware capabilities at startup, so that LLM parameters are optimized for my machine without manual configuration.

#### Acceptance Criteria

1. WHEN the backend service starts, THE Hardware_Detector SHALL collect the CPU model name, base frequency in GHz, and total number of physical cores
2. WHEN the backend service starts, THE Hardware_Detector SHALL collect the total available RAM in gigabytes
3. WHEN the backend service starts, THE Hardware_Detector SHALL detect the presence or absence of a compatible GPU and collect its name and VRAM size when present
4. THE Hardware_Detector SHALL store the collected Hardware_Info in a persistent format accessible by the Profile_Selector and the Performance_Page API
5. IF the Hardware_Detector fails to read a hardware attribute, THEN THE Hardware_Detector SHALL use a safe default value and log a warning message

### Requirement 2: Sélection automatique du profil de performance

**User Story:** As an expert, I want the system to automatically select the best performance profile for my hardware, so that the LLM runs with optimal parameters without risk of out-of-memory errors.

#### Acceptance Criteria

1. WHEN Hardware_Info indicates 32 GB or more of RAM, THE Profile_Selector SHALL select the "high" Performance_Profile with CTX_MAX of 8192 tokens and model "qwen2.5:7b-instruct-q3_K_M"
2. WHEN Hardware_Info indicates 16 GB or more but less than 32 GB of RAM, THE Profile_Selector SHALL select the "medium" Performance_Profile with CTX_MAX of 6144 tokens and model "qwen2.5:7b-instruct-q3_K_M"
3. WHEN Hardware_Info indicates 8 GB or more but less than 16 GB of RAM, THE Profile_Selector SHALL select the "low" Performance_Profile with CTX_MAX of 4096 tokens and model "qwen2.5:3b-instruct-q3_K_M"
4. IF Hardware_Info indicates less than 8 GB of RAM, THEN THE Profile_Selector SHALL select the "minimal" Performance_Profile with CTX_MAX of 2048 tokens and model "qwen2.5:3b-instruct-q3_K_M" and log a warning about degraded performance
5. THE Profile_Selector SHALL adjust the number of RAG chunks proportionally: 6 chunks for "high", 4 chunks for "medium", 3 chunks for "low", 2 chunks for "minimal"
6. THE Profile_Selector SHALL set the LLM_TOKENS_PER_SEC estimate based on detected CPU core count and frequency: base value of 8.0 tokens/s adjusted by a factor of (cores × frequency_ghz) / 16

### Requirement 3: Application dynamique des paramètres LLM

**User Story:** As an expert, I want the selected performance profile to be applied to all LLM calls, so that each workflow step uses parameters adapted to my hardware.

#### Acceptance Criteria

1. WHEN the LLM_Service processes a request, THE LLM_Service SHALL use the CTX_MAX value from the active Performance_Profile instead of the hardcoded environment variable
2. WHEN the LLM_Service processes a request, THE LLM_Service SHALL use the model name from the active Performance_Profile
3. WHEN the LLM_Service estimates duration, THE LLM_Service SHALL use the LLM_TOKENS_PER_SEC value from the active Performance_Profile
4. WHEN the active Performance_Profile changes due to a Manual_Override, THE LLM_Service SHALL apply the new parameters to subsequent requests without requiring a service restart
5. THE LLM_Service SHALL expose the active Performance_Profile parameters via an API endpoint for frontend consumption

### Requirement 4: Page Performance dans l'interface

**User Story:** As an expert, I want to see a Performance page showing my hardware configuration and the selected profile, so that I understand how the system adapts to my machine.

#### Acceptance Criteria

1. THE Performance_Page SHALL display the detected Hardware_Info: CPU model, frequency, core count, total RAM, and GPU information
2. THE Performance_Page SHALL display the name of the currently active Performance_Profile with its key parameters (model, CTX_MAX, RAG chunks)
3. THE Performance_Page SHALL display a reference table with all available Performance_Profiles showing for each: profile name, RAM range, model used, CTX_MAX tokens, RAG chunks count, and estimated duration per workflow step (Step 1 to 5)
4. THE Performance_Page SHALL highlight the row in the reference table that corresponds to the automatically detected profile
5. WHEN the Performance_Page loads, THE Performance_Page SHALL fetch the current hardware info and active profile from the backend API within 2 seconds

### Requirement 5: Override manuel du profil

**User Story:** As an expert, I want to manually override the automatically selected profile, so that I can choose a lighter profile if my machine is under heavy load or a heavier profile if I accept longer processing times.

#### Acceptance Criteria

1. THE Performance_Page SHALL provide a selection control allowing the expert to choose any available Performance_Profile as a Manual_Override
2. WHEN the expert selects a Manual_Override profile, THE Profile_Selector SHALL apply the selected profile parameters immediately and persist the choice
3. THE Performance_Page SHALL display a visual indicator distinguishing an automatically selected profile from a manually overridden profile
4. WHEN the expert selects the "Automatique" option, THE Profile_Selector SHALL revert to the automatically detected profile and clear the Manual_Override persistence
5. IF the expert selects a profile requiring more RAM than available, THEN THE Performance_Page SHALL display a warning message indicating potential instability

### Requirement 6: Estimation des durées par step

**User Story:** As an expert, I want to see estimated processing durations for each workflow step based on my profile, so that I can plan my work accordingly.

#### Acceptance Criteria

1. THE Performance_Page SHALL display estimated durations in minutes for each workflow step (Step 1 through Step 5) based on the active Performance_Profile
2. THE LLM_Service SHALL compute Step_Duration_Estimate for each step using the formula: (estimated_input_tokens × output_ratio) / LLM_TOKENS_PER_SEC, with step-specific output_ratios
3. WHEN the active Performance_Profile changes, THE Performance_Page SHALL update the displayed Step_Duration_Estimate values to reflect the new profile parameters
4. THE Performance_Page SHALL display duration estimates with a precision of one minute and a "±" tolerance indicator acknowledging variability

### Requirement 7: Téléchargement automatique du modèle adapté

**User Story:** As an expert, I want the correct LLM model to be automatically available based on my profile, so that I don't need to manually manage model downloads.

#### Acceptance Criteria

1. WHEN the selected Performance_Profile specifies a model different from the currently downloaded model, THE LLM_Service SHALL trigger a model download via Ollama pull
2. WHILE a model download is in progress, THE Performance_Page SHALL display a progress indicator with the download status
3. IF the model download fails, THEN THE LLM_Service SHALL fall back to the previously available model and log an error message
4. THE LLM_Service SHALL verify model availability at startup and report the status via the Performance API endpoint
