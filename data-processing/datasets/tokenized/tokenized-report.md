## consolidatedResult (16).tsv

### PyTransforms
#### _SentenceId_
From column: _SentenceId_
>``` python
return mtSentenceUri(getValue("SentenceId"))

```

#### _SentenceUri_
From column: _SentenceId_
>``` python
return mtSentenceUri(getValue("SentenceId"))

```

#### _AnnotationSetUri_
From column: _SentenceUri_
>``` python
return mtAnnotationSetUri(getValue("SentenceUri"))

```

#### _AnnotationClass_
From column: _Category_
>``` python
return mtAnnotationClass(getValue("Category"))
```

#### _DecodedTokensTsv_
From column: _EncodedTokens_
>``` python
return mtDecodeTokens(getValue("EncodedTokens"))
```

#### _AnnotatedTokensTsv_
From column: _TokenIdxs_
>``` python
return mtExtractAnnotatedTokens(getValue("TokenIdxs"), getValue("DecodedTokensTsv"))
```

#### _AnnotatedTokenIdxs_
From column: _TokenIdxs_
>``` python
return mtExtractAnnotatedTokenIdxs(getValue("TokenIdxs"))
```


### Semantic Types
| Column | Property | Class |
|  ----- | -------- | ----- |
| _AnnotatedTokenIdxs_ | `mturk:annotatedTokenIdxs` | `mturk:Annotation1`|
| _AnnotatedTokensTsv_ | `mturk:annotatedTokens` | `mturk:Annotation1`|
| _AnnotationClass_ | `km-dev:objectPropertySpecialization` | `mturk:AnnotationSet1`|
| _AnnotationSetUri_ | `uri` | `mturk:AnnotationSet1`|
| _AssignmentId_ | `mturk:assignmentId` | `mturk:Annotation1`|
| _DecodedTokensTsv_ | `mturk:allTokens` | `mturk:Sentence1`|
| _HitId_ | `mturk:hitId` | `mturk:Annotation1`|
| _SentenceUri_ | `uri` | `mturk:Sentence1`|
| _Text_ | `mturk:text` | `mturk:Sentence1`|
| _WorkerId_ | `mturk:workerId` | `mturk:Worker1`|


### Links
| From | Property | To |
|  --- | -------- | ---|
| `mturk:Annotation1` | `mturk:worker` | `mturk:Worker1`|
| `mturk:AnnotationSet1` | `mturk:annotation` | `mturk:Annotation1`|
| `mturk:Sentence1` | `mturk:annotationSet` | `mturk:AnnotationSet1`|
