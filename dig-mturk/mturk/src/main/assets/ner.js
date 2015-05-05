var color_classes = ['highlight_1', 'highlight_2', 'highlight_3', 'highlight_4', 'highlight_5', 'highlight_6',
		     'highlight_7', 'highlight_8', 'highlight_9', 'highlight_10', 'highlight_11', 'highlight_12'
		     ];

var categories = [];

var HTML_CONTENT = "__HTMLMARKUP__";

$(document).ready(function() {
	$('[data-toggle="tooltip"]').tooltip();

	document.getElementById('assignmentId').value = gup('assignmentId');

	categories = $('body').attr('categories').split(',');

	$(".sentence").text().replace('\t', '')
	    $(".sentence").each(function() {
		    var curr_sent = $(this);
		    var words = curr_sent.text().split(' ');
		    curr_sent.empty();
		    var spl_chars;
        var offset = 0
	    $.each(words, function(i, word) {
		    if (word == HTML_CONTENT) {
			curr_sent.append($("<span offset=" + offset + ">").text('\ufffd'));
			offset += 1;
			curr_sent.append($("<span offset=" + offset + ">").text(" "));
			offset += 1;
		    } else if (!/^[a-zA-Z0-9]*$/.test(word)) {
			var spl_chars = word.substring(word.match(/([^A-Za-z])/i).index, word.length);
			word = word.substring(0, word.match(/([^A-Za-z])/i).index)
			curr_sent.append($("<span offset=" + offset + ">").text(word));
			offset += word.length;
			curr_sent.append($("<span offset=" + offset + ">").text(spl_chars));
			offset += spl_chars.length;
			curr_sent.append($("<span offset=" + offset + ">").text(" "));
			offset += 1;
		    } else {
			curr_sent.append($("<span offset=" + offset + ">").text(word));
			offset += word.length;
			curr_sent.append($("<span offset=" + offset + ">").text(" "));
			offset += 1;
		    }
		});
		});

	/* click listener for submit button */
	$('button[name=submit]').bind("click", function(event) {
		var submit_text = "";
		var errors = {};
		
		$('div[name=parent_container]').each(function() {
			var currSent = $(this).find('div[class=sentence]').attr('id');
			if ($($(this).find('[type=checkbox]')).is(':checked')) {} else {
			    if ($(this).find('.tag_div').length > 0) {
				$(this).find('.tag_div').each(function() {
					if ($(this).find('[type=radio]:checked').length > 0) {} else {
					    errors[currSent] = "No radio button selected";
					    submit_text = '';
					}
				    });
			    } else {
				errors[currSent] = "If nothing to highlight select \"No Annotations\"";

			    }
			}
		    });

		if (!$.isEmptyObject(errors)) {
			event.preventDefault();
		    var modalHTML = "<div> <ul>";
		    for (var e in errors) {
			modalHTML += "<li><span class=\"modal-sentID\">" + e + ": </span> " + errors[e] +
			    "</li>";
		    }
		    modalHTML += "</ul> </div>";
		    $("#modal_box .modal-body").html(modalHTML);
		    $("#modal_box").modal({show: true, keyboard: true, backdrop: 'static'});
		} else {
		    /* submit to our server */
		    $("#mturk_form").submit();
	}

	    });

	/* bind events */
	$(function() {
		$(".sentence").bind("mouseup", highlightSelection);
		$('input[name^="no_annotation"]').bind("change", noAnnotationSelected);
	})

		/* Event handler for no annotation checkbox. It sets the value for the checkbox. 
	The value should be consistent with the value need for result*/
	function noAnnotationSelected() {
		var elasticSearchId = $(this).attr("elastic-search-id");
		var sentContainer = ($(this).closest(".panel-primary")).find(".sentence");
		var encodedText = $(sentContainer).attr("tokens");
		var sentText = $(sentContainer).text();
		$(this).val(elasticSearchId + "\t" + 0 + "\t" + " " + "\t" + "no annotations" + "\t" + sentText + "\t" + encodedText + "\n");
	}
	    function highlightSelection() {
	    var elasticSearchId = $(this).attr("elastic-search-id");
	    var parent_id = $(this).parent().attr('id');
	    var text = '';
	    var sentText = $(this).text();
		var encodedText = $(this).attr("tokens");
	    var char_offset = 0;
	    if (window.getSelection) { // supported by webkit and 
		sel = window.getSelection();
		rangeObject = sel.getRangeAt(0);
		//when start and end container are same; there is only one span in the selection
		if (rangeObject.startContainer == rangeObject.endContainer) {
		    //alert(rangeObject.startContainer.parentNode.id);
		    rangeObject.startContainer.parentNode.classList.add('currentSelection')
			}
		// find all spans contained in the selection
		else {
		    var begin = $(rangeObject.startContainer.parentNode);
		    var end = $(rangeObject.endContainer.parentNode);
		    //starting from begin, traverse through all the siblings till reaching end
		    $(begin).addClass('currentSelection');
		    $(begin).nextAll().each(function() {
			    var sibling = $(this);
			    if (sibling.get(0) != $(end).get(0)) {
				$(this).addClass('currentSelection');
			    } else {
				$(this).addClass('currentSelection');
				return false;
			    }
			});
		}
	    }

	    var class_to_add = '';
	    var highlight_classes = [];
	    $(this).find('span').each(function() {
		    if ($(this).hasClass('currentSelection') && $(this).is('[class^="highlight"]')) {
			if (class_to_add === '') {
			    class_to_add = $(this)[0].classList[0];
			} else {
			    var tag_span = $("#" + parent_id).find('div[id=' + $(this)[0].classList[0] +
								   ']').find('span');
			    $(tag_span).text($(tag_span).text().replace($(this).text(), ''));
			    if (!/\S/.test($(tag_span).text())) {
				$(tag_span).parent().parent().remove();
			    }
			}
		    }
		    if ($(this)[0].classList.length > 0 && $.inArray($(this)[0].classList[0],
								     highlight_classes) == -1) {
			highlight_classes.push($(this)[0].classList[0])
			    }
		});
	    highlight_classes.splice($.inArray('currentSelection', highlight_classes), 1);

	    if (class_to_add === '') {
		// choose the highlight class for current selection
		$.grep(color_classes, function(el) {
			if ($.inArray(el, highlight_classes) == -1) {
			    class_to_add = el;
			    return false;
			}
		    });
	    }

	    $(this).find('span').each(function() {
		    if ($(this).hasClass('currentSelection')) {
			$(this).removeClass();
			$(this).addClass(class_to_add);
		    }
		});
	    $(this).find('span[class=' + class_to_add + ']').each(function() {
		    text += $(this).text();
		});
	    char_offset = $($(this).find('span[class=' + class_to_add + ']:first')[0]).attr('offset')
		window.getSelection().removeAllRanges();
	
		/* Check if the selected content has at least one character*/
		if (text.replace(/^\s+|\s/g, '').length > 0) {
			if ($($('#' + parent_id).parent().find('[type=checkbox]')).is(':checked')) {
			$($('#' + parent_id).parent().find('[type=checkbox]')).attr('checked', false);
			createTagRow(parent_id, elasticSearchId, sentText, encodedText, class_to_add, text, char_offset);
			} else {
			createTagRow(parent_id, elasticSearchId, sentText, encodedText, class_to_add, text, char_offset);
			}
		}
		/* if the selected content has no characters then remove the highlights applied in the sentence*/
		else {
			$(this).find('span[class=' + class_to_add + ']').each(function() {
				$(this).removeClass(class_to_add);
			});
		}
	}

	function computeSpanClass(categoryCount) {
	    result = '';
	    switch (categoryCount) {
            case 0:
            case 1:
            case 2:
                result = 'col-xs-4 col-md-3';
                break;
            case 3:
            case 4:
            case 5:
            case 6:
            case 7:
            case 8:
            default:
                result = 'col-xs-2 col-md-3';
                break;
	    }
	    return result;
	}

	function computeRadioClass(categoryCount) {
	    result = '';
	    switch (categoryCount) {
            case 0:
            case 1:
            case 2:
                result = 'col-xs-6 col-md-3';
                break;
            case 3:
            case 4:
            case 5:
            case 6:
            case 7:
            case 8:
            default:
                result = 'col-xs-9 col-md-8';
                break;
	    }
	    return result;
	}

	function computeDeleteBtnClass(categoryCount) {
	    result = '';
	    switch (categoryCount) {
            case 0:
            case 1:
            case 2:
                result = 'col-xs-1 col-md-1';
                break;
            case 3:
            case 4:
            case 5:
            case 6:
            case 7:
            case 8:
            default:
                result = 'col-xs-1 col-md-1';
                break;
	    }
	    return result;
	}
	
	function createTagRow(fieldset_id, elasticSearchId, sentText, encodedText, class_identifier, text, char_offset) {
            var fieldset = document.getElementById(fieldset_id);
            var name = class_identifier;
            name = name.replace(/ /g, '');

            //check if the tag is a modification of some previous selection or a new selection
            if (!$('#' + fieldset_id + '>div[id=' + name + ']').length) {
                var div = document.createElement("div");
                var span_container = document.createElement("div");

                var right_triangle = document.createElement("span");

                var radio_container = document.createElement("div");
                var deleteBtn_container = document.createElement("div");
                var span = document.createElement("span");

                $(div).attr('id', name);
                $(div).attr('class', 'tag_div top-buffer row');
                $(right_triangle).attr('class', 'glyphicon glyphicon-triangle-right');

                var span_class = computeSpanClass(categories.length);
                var radio_class = computeRadioClass(categories.length);
                var deleteBtn_class = computeDeleteBtnClass(categories.length);

                $(span_container).attr('class', span_class);
                $(radio_container).attr('class', radio_class);
                $(deleteBtn_container).attr('class', deleteBtn_class);

                $(span).addClass(class_identifier);
                // span.innerHTML = text + ' length: ' + categories.length.toString() + ' radio:' + radio_class + ' span:' + span_class;
                span.innerHTML = text;

                span_container.appendChild(right_triangle);
                span_container.appendChild(span);
                div.appendChild(span_container);

                div.appendChild(radio_container);

                $.each(categories, function(key, value) {
			var label = document.createElement("label");

			$(label).attr('class', 'radio-inline');

			$('<input />', {
				type: "radio",
				    name: fieldset_id + name,
				    value: elasticSearchId + "\t" + char_offset + "\t" + text + "\t" +
				    value + "\t" + sentText + "\t" + encodedText+"\n",
				    }).appendTo(label).after(value);

			radio_container.appendChild(label);
		    });



                $('<button/>', {
			class: 'deleteBtn glyphicon glyphicon-remove',
			    name: 'deleteTag'
			    }).appendTo(deleteBtn_container);


                div.appendChild(deleteBtn_container);
                fieldset.appendChild(div);
            } else {
                /* At times, while over-riding existing selection, the previous selction text goes into ::before of the glyphicon. So empty it.*/
                $('#' + fieldset_id + '>div[id=' + name + ']').find('.glyphicon-triangle-right').empty();
                $('#' + fieldset_id + '>div[id=' + name + ']').find('span[class=' + class_identifier + ']').text(
														 text);
            }
        }
        /* click listener for delete button*/
	$(document).on("click", "button[name=deleteTag]", function() {
		var curr_id = $(this).parent().parent().attr('id');
		//remove selected tag's highlight in the main sentence
		$(this).parent().parent().parent().find('span[class=' + curr_id + ']').removeClass();
		//remove tag component
		$(this).parent().parent().remove();
	    });


    });

function gup(name) {
    var regexS = "[\\?&]" + name + "=([^&#]*)";
    var regex = new RegExp(regexS);
    var tmpURL = window.location.href;
    var results = regex.exec(tmpURL);
    if (results === null)
        return "";
    else
        return results[1];
}