"""Prompts do 2D: um estilo único, montado em camadas (estilo, categoria e o tema opcional).

Estilo e categorias aprovados no teste de 19/11 (`docs/prompts/`, rodada r3); temas, no de 25/11.
Mudar um prompt exige rodar o teste de novo. Suba `PROMPT_VERSION` a cada mudança: cada
`ProviderTask` guarda a versão e o texto enviado.
"""

from catalog.categories import Category
from catalog.themes import Theme

PROMPT_VERSION = "2026-11-25"

MAX_PRINT_COLORS = 4
# Colors we have PLA filament for: name sent to the image model -> hex. Starting values
# are the common PLA colors; replace them with the real stock.
FILAMENT_COLORS = {
    "white": "#FFFFFF",
    "black": "#000000",
    "gray": "#8E9089",
    "red": "#C12E1F",
    "orange": "#FF6A13",
    "yellow": "#F4EE2A",
    "green": "#00AE42",
    "blue": "#0A2989",
    "purple": "#5E43B7",
    "pink": "#F5547C",
    "brown": "#9D432C",
    "beige": "#F7E6DE",
    # Voolt3D PLA "Bege Caucasiano". The maker publishes no hex: sampled from its product photo.
    "light skin": "#EBC8B0",
}
# Opens every prompt that produces a 2D image; at the end of the prompt, GPT Image 2 kept the
# off-list colors of requests and references. Tested 2026-11-02, one image per case: off-list
# colors were replaced in 3 of 4 cases, but only 1 of 6 images stayed within the limit, so
# this lowers the color count without guaranteeing it.
_COLOR_RULE = (
    "This figurine is 3D printed, and only these filament colors exist: "
    + ", ".join(f"{name} ({hex_code})" for name, hex_code in FILAMENT_COLORS.items())
    + f". No other color can be printed. Use at most {MAX_PRINT_COLORS} of them on the whole "
    "figurine, counting the base and small details such as eyes, mouth and buttons. Do not "
    "reproduce colors from the request or the reference that are not on the list, such as "
    "turquoise, teal, gold, tan or light blue: repaint them in the closest listed color, "
    "even if that changes how it looks. Each part is one uniform matte color but stays a "
    "sculpted 3D form with volume, never a flat drawing. The white background does not count "
    "as a color. Do not draw the list, color swatches or any text.\n\n"
)

# --- Estilo único (o antigo "Pixar") ---

_LOOK = "soft rounded stylized forms, clean smooth materials, a warm friendly look."
_KEEP = (
    "same faces, features, hair, clothing and distinctive details, and do not add anyone or "
    "anything that is not in the reference."
)
_STYLE = (
    "Turn the main subject of this reference image into a 3D model from a modern animated "
    f"family movie: {_LOOK} Keep it recognizably the same: {_KEEP}"
)
# O tema troca acessórios e roupa, então a lista do que manter não inclui a roupa.
_STYLE_WITH_THEME = (
    "Turn the main subject of this reference image into a 3D model from a modern animated "
    "family movie, dressed up for a theme: {theme} Style: "
    f"{_LOOK} Apart from the theme, keep it recognizably the same: same faces, features, hair and "
    "distinctive details, and do not add anyone or anything else that is not in the reference."
)

# Sem estas regras, braços, pernas e dedos saíam finos demais para uma peça de 6 cm.
_PRINT_RULES = (
    "It will be 3D printed as a small figurine, so it must be sturdy: chunky simplified forms, "
    "thick arms and legs, simple hands with the fingers together, kept close to the body or "
    "touching it, nothing thin sticking out, and ears, tails and accessories attached to the body."
)
_FRAME = (
    "Ignore the background and whatever is underneath the subject. Whole subject alone, "
    "centered and large, with a clear white margin on every side so that nothing touches the "
    "edge of the image, standing on a small plain round base in the figure's dark color, "
    "isolated on a plain white background with a soft contact shadow."
)

# --- Categoria ---

_PROPORTIONS = (
    "stylized proportions about four heads tall, a head only slightly larger than realistic and "
    "large expressive eyes"
)
_ANIMAL = (
    "keeps its natural body and anatomy, slightly stylized, with a friendly cartoon face and big "
    "expressive eyes"
)
# Sem o bloco, "o assunto principal" fazia o modelo gerar uma pessoa só: 7 de 8 casais e
# pessoas com pet perderam a segunda figura. Casal e Pessoa + Pet são uma peça só (RN-35).
_CATEGORY = {
    Category.PERSON: (
        f"The subject is one person. Give them {_PROPORTIONS}, and show them full body, standing "
        "on both feet with the arms relaxed at the sides, even if the photo shows only part of "
        "them."
    ),
    Category.PET: (
        f"The subject is one animal. It {_ANIMAL}, shown whole in a calm, compact natural pose, "
        "sitting or standing, even if the photo shows only part of it."
    ),
    Category.COUPLE: (
        "The subject is two people, made as one single figurine. Both are shown full body, "
        "standing side by side and touching, with an arm around each other or holding hands, so "
        f"that the two figures are joined into one piece. Give both {_PROPORTIONS}. The two "
        "figures share the same few colors."
    ),
    Category.PERSON_PET: (
        "The subject is one person with one animal, made as one single figurine. The person is "
        f"shown full body, standing, with {_PROPORTIONS}, holding the animal in their arms or "
        "with the animal sitting at their feet pressed against their legs, so that they are "
        "joined into one piece. If the animal is too large to hold, it stands right beside the "
        f"person, touching them, scaled down to fit. The animal {_ANIMAL}. Person and animal "
        "share the same few colors."
    ),
}

# --- Plano de cores por categoria ---

_SKIN = "skin (light skin, or brown for dark skin)"
_COLOR_PLAN_START = (
    "\n\nColor plan, more important than color accuracy: the finished figurine, base included, "
    f"uses exactly {MAX_PRINT_COLORS} colors from the list, no more, and each part is one flat "
    "color with no prints, patterns, stripes or logos. These rules change only the colors, never "
    "what the subject is: every shape and feature above stays. "
)
_COLOR_PLAN_END = " Do not add any person, animal or object that is not in the reference."
_COLOR_PLAN = {
    Category.PERSON: (
        f"Use {_SKIN}; one dark color (black or brown) shared by the hair, beard, eyebrows, eyes, "
        "shoes and base; one color for the top; and one color for the trousers or skirt. A dress "
        "or one-piece outfit is a single color."
    ),
    Category.PET: (
        "Use the animal's main color; a second color for its largest marking, or for the belly, "
        "muzzle or chest; black shared by the eyes, nose and base; and one color for a collar or "
        "accessory, if it has one. Beak, paws, claws, mouth and tongue reuse one of these colors."
    ),
    Category.COUPLE: (
        f"The two people share the same {MAX_PRINT_COLORS} colors: {_SKIN}; one dark color "
        "(black or brown) shared by both people's hair, eyes, shoes and the base; one color for "
        "one person's clothes; and one color for the other person's clothes. Trousers, ties and "
        "flowers reuse one of these colors. If their skin tones differ, light skin and brown both "
        "count, so the two outfits share one color."
    ),
    Category.PERSON_PET: (
        f"The person and the animal share the same {MAX_PRINT_COLORS} colors: {_SKIN}; one dark "
        "color (black or brown) shared by the person's hair, eyes and shoes, the animal's eyes and "
        "nose, and the base; one color for all of the person's clothes; and one color for the "
        "animal's fur, feathers or coat. The animal's markings, mouth and tongue, and any "
        "accessory, reuse one of these colors."
    ),
}

# --- Tema ---
# Uma versão por categoria: o gorro no cachorro é diferente do gorro no casal. O tema só põe
# acessórios e roupa, nunca pessoas ou animais (a classificação da versão mudaria a categoria),
# e tudo fica grosso e encostado no corpo. Marcas e jogos não são citados: o modelo recusa
# propriedade intelectual, então o prompt descreve o visual.

_SANTA_HAT = (
    "a red Santa Claus hat with a thick white fur band and a white pom-pom, fitted snugly on the "
    "head, with its tip folded down against the side of the hat and the pom-pom resting on it"
)
_PET_SANTA_HAT = (
    "a small red Santa Claus hat with a thick white fur band and a white pom-pom, fitted snugly "
    "on its head between the ears, with its tip folded down against the hat"
)
_SUNGLASSES = "dark aviator sunglasses"
_MIAMI_SHIRT = "a short-sleeve 1980s Miami-style shirt, worn open at the collar"
# Apontada para baixo e encostada na coxa: imprimível e sem ameaça na pose.
_PISTOL = (
    "a chunky, rounded cartoon pistol held in one hand, pointing at the ground and pressed flat "
    "against the outside of the thigh, touching it"
)
_THEME = {
    Theme.CHRISTMAS: {
        Category.PERSON: (
            f"Christmas. They wear {_SANTA_HAT}, and a cozy red Christmas sweater as their top."
        ),
        Category.PET: (
            f"Christmas. It wears {_PET_SANTA_HAT}, and a small red scarf wrapped snugly around "
            "its neck."
        ),
        Category.COUPLE: (
            f"Christmas. Both people wear {_SANTA_HAT}, and a cozy red Christmas sweater as their "
            "top."
        ),
        Category.PERSON_PET: (
            f"Christmas. The person wears {_SANTA_HAT}, and a cozy red Christmas sweater as their "
            f"top. The animal wears {_PET_SANTA_HAT}."
        ),
    },
    Theme.GTA6: {
        Category.PERSON: (
            f"a 1980s Miami crime movie. They wear {_SUNGLASSES} and {_MIAMI_SHIRT}, with "
            f"{_PISTOL}."
        ),
        Category.PET: (
            f"a 1980s Miami crime movie. It wears {_SUNGLASSES} resting on its face and a small "
            "bandana tied snugly around its neck."
        ),
        Category.COUPLE: (
            f"a 1980s Miami crime movie. Both people wear {_SUNGLASSES} and {_MIAMI_SHIRT}. One "
            f"of them has {_PISTOL}; the other's hand stays on their partner."
        ),
        Category.PERSON_PET: (
            f"a 1980s Miami crime movie. The person wears {_SUNGLASSES} and {_MIAMI_SHIRT}, with "
            f"{_PISTOL}, and the animal sits at their feet pressed against their legs. The "
            f"animal wears {_SUNGLASSES} resting on its face."
        ),
    },
}

# Com tema, o plano de cores da categoria dá lugar a este: o tema traz as próprias cores e ainda
# precisa caber nas quatro.
_THEME_COLOR_PLAN = {
    Theme.CHRISTMAS: {
        Category.PERSON: (
            f"Use {_SKIN}; one dark color (black or brown) shared by the hair, beard, eyebrows, "
            "eyes, trousers or skirt, shoes and base; red for the Santa hat and the sweater; and "
            "white for the hat's fur band and pom-pom."
        ),
        Category.PET: (
            "Use the animal's main color; black shared by the eyes, nose and base; red for the "
            "Santa hat and the scarf; and white for the hat's fur band and pom-pom, also used for "
            "a light marking, belly, muzzle or chest. Other markings, paws, mouth and tongue reuse "
            "one of these colors."
        ),
        Category.COUPLE: (
            f"The two people share the same {MAX_PRINT_COLORS} colors: {_SKIN}; one dark color "
            "(black or brown) shared by both people's hair, eyes, trousers or skirts, shoes and "
            "the base; red for both Santa hats and both sweaters; and white for the hats' fur "
            "bands and pom-poms. If their skin tones differ, light skin and brown both count, so "
            "the fur bands and pom-poms reuse light skin."
        ),
        Category.PERSON_PET: (
            f"The person and the animal share the same {MAX_PRINT_COLORS} colors: {_SKIN}; one "
            "dark color (black or brown) shared by the person's hair, eyes, trousers and shoes, "
            "the animal's eyes and nose, and the base; red for both Santa hats and the sweater; "
            "and the animal's fur color, also used for both hats' fur bands and pom-poms. The "
            "animal's markings, mouth and tongue reuse one of these colors."
        ),
    },
    Theme.GTA6: {
        Category.PERSON: (
            f"Use {_SKIN}; black shared by the hair, eyebrows, eyes, sunglasses, pistol, shoes "
            "and base; pink for the shirt; and white for the trousers or skirt."
        ),
        Category.PET: (
            "Use the animal's main color; a second color for its largest marking, or for the "
            "belly, muzzle or chest; black shared by the eyes, nose, sunglasses and base; and pink "
            "for the bandana. Beak, paws, claws, mouth and tongue reuse one of these colors."
        ),
        Category.COUPLE: (
            f"The two people share the same {MAX_PRINT_COLORS} colors: {_SKIN}; black shared by "
            "both people's hair, eyes, sunglasses, the pistol, belts, shoes and the base; pink for "
            "all of one person's clothes, trousers or skirt included; and purple for all of the "
            "other person's clothes, trousers or skirt included. If their skin tones differ, light "
            "skin and brown both count, so both outfits are pink."
        ),
        Category.PERSON_PET: (
            f"The person and the animal share the same {MAX_PRINT_COLORS} colors: {_SKIN}; black "
            "shared by the person's hair, eyes and shoes, both pairs of sunglasses, the pistol, "
            "the animal's eyes and nose, and the base; pink for all of the person's clothes; and "
            "one color for the animal's fur, feathers or coat. The animal's markings, mouth and "
            "tongue reuse one of these colors."
        ),
    },
}
_COLOR_PLAN_END_WITH_THEME = (
    " Do not add any person, animal or object that is not in the reference, apart from the "
    "theme's accessories."
)

# Sent with the current image as reference. Tested 2026-11-01: vague requests ("make it
# prettier") otherwise lose the white background, which print preparation relies on.
_EDIT = "{instruction}. Keep everything else exactly the same, on a plain white background"


def photo_prompt(*, category: str, theme: str = "") -> str:
    """A foto do cliente vira a imagem da figura na categoria detectada, com o tema, se houver."""
    category = Category(category)
    if theme:
        theme = Theme(theme)
        style = _STYLE_WITH_THEME.replace("{theme}", _THEME[theme][category])
        color_plan = _THEME_COLOR_PLAN[theme][category] + _COLOR_PLAN_END_WITH_THEME
    else:
        style = _STYLE
        color_plan = _COLOR_PLAN[category] + _COLOR_PLAN_END
    return (
        f"{_COLOR_RULE}{style} {_CATEGORY[category]} {_PRINT_RULES} {_FRAME}"
        f"{_COLOR_PLAN_START}{color_plan}"
    )


def edit_prompt(*, instruction: str) -> str:
    return _COLOR_RULE + _EDIT.replace("{instruction}", instruction.strip().rstrip("."))
