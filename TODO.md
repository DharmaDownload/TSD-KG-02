On a trois trucs à faire décider par les utilisateurs :
- selection de layers
- format outputs (rtf, txt, docx, tei) 
- présentation des annotations (footnotes, toc,...)

Et faut avoir un format basique en texte par défaut, pour éditer et updater un layer

Definitions:
- `base`: Exact reproduction of a physical edition of a text. 
          It only reproduces the textual content, leaving aside all the 
          layout except for new lines 

- `layer`: A set of modifications to the base.
           Implemented as a file of patches bearing the `.layer` extension.

- `modification`: An individual difference from the base that is rendered in a layer.
                  Implemented as an individual patch within a layer file.

- `layer-basis`: The state of the text that a given layer is expecting 
                 as its basis. Must be an export view, either the base itself 
                 or the result of applying any number of layers.

- `view`: generic term to refer to the output(a .txt file) of applying any number of layers to the base. 
        Must be either an `edit-view` or an `export-view`

- `edit-view`: a `view` where each modification is presented inline using [Critic Markup](http://criticmarkup.com/users-guide.php)     

- `export-view`: a `view` containing the result of the application of 

- `edited-view`: a manually edited `edit-view`. if there is no edition, the user is notified and the update is aborted


# Development

## Step 1: Basis

 - creates a new ePecha
 - load an existing one
 - create a new layer (writes patches in a human friendly format)
 - export views (default + CM)
 - exports patches that couldn't be applied

TODO: 

 - put dependencies of each layer as a header
 - add header for all failing matches: '<number>\t"<modified>"\t"<original>"\t"<patch info>"\n'

id persistant
    base layer
    layer
    annotation


ajouter un header dans les docx exportés

make 