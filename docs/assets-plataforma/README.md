# Imagens da plataforma

Imagens que a própria plataforma mostra, no bucket público `eumini-assets`, carregadas direto pelo navegador ([ARQUITETURA §15](../ARQUITETURA.md#imagens-da-plataforma-bucket-público)).

## Categorias da home

| | |
|---|---|
| **Data** | 23/11/2026 |
| **Onde aparecem** | Na vitrine da home (`CategoryPicker`), no lugar dos ícones |
| **Arquivos** | `categorias/<categoria>-v1.webp`, 256 px, enviados para `categories/` do bucket |
| **Escolhidas** | `person-1`, `pet-1`, `couple-1`, `person_pet-1` |
| **Custo** | US$ 0,44 pelas 12 variações (foto e miniatura) |

### Como foram feitas

- **Fotos de entrada sintéticas:** cada foto foi gerada por texto na Runware, com pessoas e pets fictícios. Assim não há direito de imagem de ninguém na home.
- **Miniatura:** cada foto passou pelo prompt de produção (`catalog/prompts.py`, versão `2026-11-19`), na Runware, como o worker faz.
- **Escolha:** foram 3 variações por categoria. A folha com foto e miniatura lado a lado está em [`categorias/geracao/folha.jpg`](categorias/geracao/folha.jpg), e os prompts e custos em `categorias/geracao/resultado.json`.
- **Acabamento:** a margem branca foi recortada e a imagem ficou quadrada, em WebP de 256 px.

### Para trocar ou refazer

A partir da raiz:

```
apps/backend/.venv/Scripts/python.exe -I docs/assets-plataforma/gerar_categorias.py gerar
apps/backend/.venv/Scripts/python.exe -I docs/assets-plataforma/gerar_categorias.py finalizar person-1 pet-1 couple-1 person_pet-1
```

O cache dessas imagens é permanente. Para trocar uma imagem:

1. Suba a `VERSAO` no script e gere `-v2`.
2. Aponte `image()` em `apps/web/consumer/src/features/catalog/categories.ts` para o nome novo.
3. Depois do `aws login`, envie a partir de `apps/backend`:

```
.venv/Scripts/python.exe scripts/provision_s3.py --upload-assets
```

O bucket é o mesmo em todos os ambientes, então não há nada a fazer no lançamento.

## Temas do envio da foto

| | |
|---|---|
| **Data** | 25/11/2026 |
| **Onde aparecem** | Nos cards de tema, abaixo da foto, na página da categoria (`PromptStep`). "Sem tema" usa a miniatura da própria categoria |
| **Arquivos** | `temas/<tema>-v1.webp`, 256 px, enviados para `themes/` do bucket |
| **Escolhidas** | `christmas-pet-1` e `gta6-person-2` |
| **Custo** | US$ 0,09 pelas 4 variações |

As fotos de entrada são as sintéticas das categorias (`categorias/geracao/<variação>-foto.png`), passadas pelo prompt de produção com o tema (versão `2026-11-25`). A folha está em [`temas/geracao/folha.jpg`](temas/geracao/folha.jpg). Para refazer, a partir da raiz:

```
apps/backend/.venv/Scripts/python.exe -I docs/assets-plataforma/gerar_temas.py gerar
apps/backend/.venv/Scripts/python.exe -I docs/assets-plataforma/gerar_temas.py finalizar christmas-pet-1 gta6-person-2
```

Um tema novo precisa de uma entrada em `VARIACOES` no script e em `THEMES` (`apps/web/consumer/src/features/catalog/themes.ts`). Trocar uma imagem segue o mesmo caminho das categorias: nova versão, nome novo e `provision_s3.py --upload-assets`.
