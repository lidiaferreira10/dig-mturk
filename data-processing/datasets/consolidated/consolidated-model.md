## consolidatedResult-eyehair67.tsv

### PyTransforms
#### _annotationClass_
From column: _category_
>``` python
return mtAnnotationClass(getValue("category"))
```

#### _sentenceUri_
From column: _sentenceId_
>``` python
return mtSentenceUri(getValue("sentenceId"))
```


### Semantic Types
| Column | Property | Class |
|  ----- | -------- | ----- |
| _ WorkerId_ | `mturk:workerId` | `mturk:Worker1`|
| _AssignmentId_ | `mturk:assignmentId` | `mturk:Annotation1`|
| _HitId_ | `mturk:hitId` | `mturk:Annotation1`|
| _annotationClass_ | `km-dev:objectPropertySpecialization` | `mturk:AnnotationSet1`|
| _hightlight_text_ | `mturk:value` | `mturk:Annotation1`|
| _offset_ | `mturk:offset` | `mturk:Annotation1`|
| _sentenceUri_ | `uri` | `mturk:Sentence1`|
| _text_ | `mturk:text` | `mturk:Sentence1`|


### Links
| From | Property | To |
|  --- | -------- | ---|
| `mturk:Annotation1` | `mturk:worker` | `mturk:Worker1`|
| `mturk:AnnotationSet1` | `mturk:annotation` | `mturk:Annotation1`|
| `mturk:Sentence1` | `mturk:annotationSet` | `mturk:AnnotationSet1`|
