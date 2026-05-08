"use client";

import { useState, useCallback, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError } from "@/lib/api";
import ReCaptchaWidget from "@/components/ReCaptchaWidget";
import styles from "./inscription.module.css";

const DOMAINES = [
  "psychologie",
  "psychiatrie",
  "médecine légale",
  "bâtiment",
  "comptabilité",
] as const;

interface FormData {
  nom: string;
  prenom: string;
  adresse: string;
  ville: string;
  codePostal: string;
  telephone: string;
  domaine: string;
  email: string;
  password: string;
  acceptMentions: boolean;
  acceptCGU: boolean;
  acceptProtection: boolean;
  acceptNewsletter: boolean;
}

interface FormErrors {
  nom?: string;
  prenom?: string;
  adresse?: string;
  ville?: string;
  codePostal?: string;
  telephone?: string;
  domaine?: string;
  email?: string;
  password?: string;
  acceptMentions?: string;
  acceptCGU?: string;
  acceptProtection?: string;
}

export default function InscriptionPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [formData, setFormData] = useState<FormData>({
    nom: "",
    prenom: "",
    adresse: "",
    ville: "",
    codePostal: "",
    telephone: "",
    domaine: "",
    email: "",
    password: "",
    acceptMentions: false,
    acceptCGU: false,
    acceptProtection: false,
    acceptNewsletter: false,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);

  const [showEncryptionPopup, setShowEncryptionPopup] = useState(false);

  const handleCaptchaVerify = useCallback((token: string) => {
    setCaptchaToken(token);
  }, []);

  const handleCaptchaExpire = useCallback(() => {
    setCaptchaToken(null);
  }, []);

  function updateField(field: keyof FormData, value: string | boolean) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (field in errors) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field as keyof FormErrors];
        return next;
      });
    }
  }

  function validate(): FormErrors {
    const errs: FormErrors = {};
    if (!formData.nom.trim()) errs.nom = "Le nom est requis";
    if (!formData.prenom.trim()) errs.prenom = "Le prénom est requis";
    if (!formData.adresse.trim()) errs.adresse = "L'adresse est requise";
    if (!formData.ville.trim()) errs.ville = "La ville est requise";
    if (!formData.codePostal.trim()) {
      errs.codePostal = "Le code postal est requis";
    } else if (!/^\d{5}$/.test(formData.codePostal.trim())) {
      errs.codePostal = "Le code postal doit contenir 5 chiffres";
    }
    if (!formData.telephone.trim()) {
      errs.telephone = "Le téléphone est requis";
    } else if (!/^(\+33|0)\d{9}$/.test(formData.telephone.trim().replace(/\s/g, ""))) {
      errs.telephone = "Format de téléphone invalide (ex: 0612345678)";
    }
    if (!formData.domaine) errs.domaine = "Veuillez sélectionner un domaine";
    if (!formData.email.trim()) {
      errs.email = "L'email est requis";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errs.email = "Format d'email invalide";
    }
    if (!formData.password) {
      errs.password = "Le mot de passe est requis";
    } else if (formData.password.length < 8) {
      errs.password = "Le mot de passe doit contenir au moins 8 caractères";
    }
    if (!formData.acceptMentions)
      errs.acceptMentions = "Vous devez accepter les Mentions légales";
    if (!formData.acceptCGU)
      errs.acceptCGU = "Vous devez accepter les CGU";
    if (!formData.acceptProtection)
      errs.acceptProtection = "Vous devez vous engager à protéger les données";
    return errs;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");

    const validationErrors = validate();
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    if (!captchaToken) {
      setSubmitError("Veuillez valider le captcha");
      return;
    }

    setIsSubmitting(true);
    try {
      await register({
        nom: formData.nom.trim(),
        prenom: formData.prenom.trim(),
        adresse: formData.adresse.trim(),
        ville: formData.ville.trim(),
        code_postal: formData.codePostal.trim(),
        telephone: formData.telephone.trim().replace(/\s/g, ""),
        domaine: formData.domaine,
        email: formData.email.trim(),
        password: formData.password,
        acceptMentions: formData.acceptMentions,
        acceptCGU: formData.acceptCGU,
        acceptProtection: formData.acceptProtection,
        acceptNewsletter: formData.acceptNewsletter,
      });

      setSubmitSuccess("Inscription réussie ! Un email de confirmation vous a été envoyé. Vérifiez votre boîte de réception pour activer votre compte.");
      setFormData({
        nom: "", prenom: "", adresse: "", ville: "", codePostal: "", telephone: "",
        domaine: "", email: "", password: "",
        acceptMentions: false, acceptCGU: false, acceptProtection: false, acceptNewsletter: false,
      });
      // Rediriger vers la page de confirmation après 2 secondes
      const registeredEmail = formData.email.trim();
      setTimeout(() => router.push(`/confirmation?email=${encodeURIComponent(registeredEmail)}`), 2000);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setSubmitError("Un compte avec cet email existe déjà.");
      } else {
        setSubmitError("Erreur lors de l'inscription. Veuillez réessayer.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Créer un compte</h1>
      <p className={styles.subtitle}>
        Inscrivez-vous pour accéder aux services Judi-expert
      </p>

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        {submitError && (
          <div className={styles.errorMessage} role="alert">{submitError}</div>
        )}
        {submitSuccess && (
          <div className={styles.successMessage} role="status">{submitSuccess}</div>
        )}

        <div className={styles.row}>
          <div className={styles.fieldGroup}>
            <label htmlFor="nom" className={styles.label}>
              Nom<span className={styles.required}>*</span>
            </label>
            <input id="nom" type="text"
              className={`${styles.input} ${errors.nom ? styles.inputError : ""}`}
              value={formData.nom} onChange={(e) => updateField("nom", e.target.value)}
              required aria-invalid={!!errors.nom}
              aria-describedby={errors.nom ? "nom-error" : undefined} />
            {errors.nom && <p id="nom-error" className={styles.fieldError}>{errors.nom}</p>}
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="prenom" className={styles.label}>
              Prénom<span className={styles.required}>*</span>
            </label>
            <input id="prenom" type="text"
              className={`${styles.input} ${errors.prenom ? styles.inputError : ""}`}
              value={formData.prenom} onChange={(e) => updateField("prenom", e.target.value)}
              required aria-invalid={!!errors.prenom}
              aria-describedby={errors.prenom ? "prenom-error" : undefined} />
            {errors.prenom && <p id="prenom-error" className={styles.fieldError}>{errors.prenom}</p>}
          </div>
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="adresse" className={styles.label}>
            Adresse<span className={styles.required}>*</span>
          </label>
          <textarea id="adresse"
            className={`${styles.textarea} ${errors.adresse ? styles.inputError : ""}`}
            value={formData.adresse} onChange={(e) => updateField("adresse", e.target.value)}
            required aria-invalid={!!errors.adresse}
            aria-describedby={errors.adresse ? "adresse-error" : undefined} />
          {errors.adresse && <p id="adresse-error" className={styles.fieldError}>{errors.adresse}</p>}
        </div>

        <div className={styles.row}>
          <div className={styles.fieldGroup}>
            <label htmlFor="codePostal" className={styles.label}>
              Code postal<span className={styles.required}>*</span>
            </label>
            <input id="codePostal" type="text" maxLength={5}
              className={`${styles.input} ${errors.codePostal ? styles.inputError : ""}`}
              value={formData.codePostal} onChange={(e) => updateField("codePostal", e.target.value)}
              required placeholder="75001" aria-invalid={!!errors.codePostal}
              aria-describedby={errors.codePostal ? "codePostal-error" : undefined} />
            {errors.codePostal && <p id="codePostal-error" className={styles.fieldError}>{errors.codePostal}</p>}
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="ville" className={styles.label}>
              Ville<span className={styles.required}>*</span>
            </label>
            <input id="ville" type="text"
              className={`${styles.input} ${errors.ville ? styles.inputError : ""}`}
              value={formData.ville} onChange={(e) => updateField("ville", e.target.value)}
              required placeholder="Paris" aria-invalid={!!errors.ville}
              aria-describedby={errors.ville ? "ville-error" : undefined} />
            {errors.ville && <p id="ville-error" className={styles.fieldError}>{errors.ville}</p>}
          </div>
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="telephone" className={styles.label}>
            Téléphone<span className={styles.required}>*</span>
          </label>
          <input id="telephone" type="tel"
            className={`${styles.input} ${errors.telephone ? styles.inputError : ""}`}
            value={formData.telephone} onChange={(e) => updateField("telephone", e.target.value)}
            required placeholder="06 12 34 56 78" aria-invalid={!!errors.telephone}
            aria-describedby={errors.telephone ? "telephone-error" : undefined} />
          {errors.telephone && <p id="telephone-error" className={styles.fieldError}>{errors.telephone}</p>}
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="domaine" className={styles.label}>
            Domaine d&apos;expertise<span className={styles.required}>*</span>
          </label>
          <select id="domaine"
            className={`${styles.select} ${errors.domaine ? styles.inputError : ""}`}
            value={formData.domaine} onChange={(e) => updateField("domaine", e.target.value)}
            required aria-invalid={!!errors.domaine}
            aria-describedby={errors.domaine ? "domaine-error" : undefined}>
            <option value="">— Sélectionnez un domaine —</option>
            {DOMAINES.map((d) => (
              <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
            ))}
          </select>
          {errors.domaine && <p id="domaine-error" className={styles.fieldError}>{errors.domaine}</p>}
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="email" className={styles.label}>
            Email<span className={styles.required}>*</span>
          </label>
          <input id="email" type="email"
            className={`${styles.input} ${errors.email ? styles.inputError : ""}`}
            value={formData.email} onChange={(e) => updateField("email", e.target.value)}
            required autoComplete="email" aria-invalid={!!errors.email}
            aria-describedby={errors.email ? "email-error" : undefined} />
          {errors.email && <p id="email-error" className={styles.fieldError}>{errors.email}</p>}
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="password" className={styles.label}>
            Mot de passe<span className={styles.required}>*</span>
          </label>
          <input id="password" type="password"
            className={`${styles.input} ${errors.password ? styles.inputError : ""}`}
            value={formData.password} onChange={(e) => updateField("password", e.target.value)}
            required autoComplete="new-password" aria-invalid={!!errors.password}
            aria-describedby={errors.password ? "password-error" : undefined} />
          {errors.password && <p id="password-error" className={styles.fieldError}>{errors.password}</p>}
        </div>

        <div className={styles.checkboxGroup}>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={formData.acceptMentions}
              onChange={(e) => updateField("acceptMentions", e.target.checked)}
              aria-invalid={!!errors.acceptMentions} />
            <span>J&apos;ai lu et j&apos;accepte les <Link href="/mentions-legales">Mentions légales</Link><span className={styles.required}>*</span></span>
          </label>
          {errors.acceptMentions && <p className={styles.fieldError}>{errors.acceptMentions}</p>}

          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={formData.acceptCGU}
              onChange={(e) => updateField("acceptCGU", e.target.checked)}
              aria-invalid={!!errors.acceptCGU} />
            <span>J&apos;ai lu et j&apos;accepte les <Link href="/cgu">CGU</Link><span className={styles.required}>*</span></span>
          </label>
          {errors.acceptCGU && <p className={styles.fieldError}>{errors.acceptCGU}</p>}

          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={formData.acceptProtection}
              onChange={(e) => updateField("acceptProtection", e.target.checked)}
              aria-invalid={!!errors.acceptProtection} />
            <span>
              J&apos;ai pris connaissance de la <Link href="/politique-confidentialite">Politique de confidentialité</Link> et des <Link href="/securite">mesures de sécurité</Link>, et je m&apos;engage à protéger les données sur mon PC (BitLocker ou équivalent)<span className={styles.required}>*</span>
              {" "}
              <button type="button" className={styles.infoBtn} onClick={() => setShowEncryptionPopup(true)} aria-label="En savoir plus sur le chiffrement">ℹ️</button>
            </span>
          </label>
          {errors.acceptProtection && <p className={styles.fieldError}>{errors.acceptProtection}</p>}

          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={formData.acceptNewsletter}
              onChange={(e) => updateField("acceptNewsletter", e.target.checked)} />
            <span>J&apos;accepte de recevoir des emails et la newsletter</span>
          </label>
        </div>

        {showEncryptionPopup && (
          <div className={styles.popupOverlay} onClick={() => setShowEncryptionPopup(false)}>
            <div className={styles.popupContent} onClick={(e) => e.stopPropagation()}>
              <h3 className={styles.popupTitle}>🔒 Obligation de chiffrement des données</h3>
              <p>
                En tant qu&apos;expert judiciaire, vous manipulez des données sensibles
                soumises au secret professionnel. Le RGPD et l&apos;AI Act européen imposent
                la mise en place de mesures techniques appropriées pour protéger ces données.
              </p>
              <p>
                <strong>Le chiffrement intégral du disque est obligatoire</strong> sur le poste
                où l&apos;application Judi-expert est installée :
              </p>
              <ul>
                <li><strong>Windows :</strong> BitLocker (inclus dans Windows Pro/Enterprise)</li>
                <li><strong>macOS :</strong> FileVault (inclus dans macOS)</li>
                <li><strong>Linux :</strong> LUKS (chiffrement natif)</li>
              </ul>
              <p>
                Cette mesure garantit que les données d&apos;expertise restent inaccessibles
                en cas de perte ou de vol de votre ordinateur.
              </p>
              <button type="button" className={styles.popupClose} onClick={() => setShowEncryptionPopup(false)}>
                Compris
              </button>
            </div>
          </div>
        )}

        <div className={styles.captchaBox}>
          <ReCaptchaWidget onVerify={handleCaptchaVerify} onExpire={handleCaptchaExpire} />
        </div>

        <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
          {isSubmitting ? "Inscription en cours…" : "S'inscrire"}
        </button>
      </form>

      <p className={styles.loginLink}>
        Déjà inscrit ? <Link href="/connexion">Se connecter</Link>
      </p>
    </div>
  );
}
