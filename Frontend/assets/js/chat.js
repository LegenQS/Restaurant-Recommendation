var checkout = {};

let index = 0

$(document).ready(function() {
  var $messages = $('.messages-content'),
    d, h, m,
    i = 0;


  // func: add scroll bar and display the first message. 
  $(window).load(function() {
    $messages.mCustomScrollbar();
    insertResponseMessage('Hi there, I\'m your personal Concierge. How can I help?');
  });

  // function updateScrollbar() {
  //   $messages.mCustomScrollbar("update").mCustomScrollbar('scrollTo', 'bottom', {
  //     scrollInertia: 10,
  //     timeout: 0
  //   });
  // }

  function updateScrollbar() {
    console.log('update scroll bar position.')
    // let curId = "conv" + index
    // let $curEle = $('#' + curId)
    // $messages.mCustomScrollbar("update").mCustomScrollbar('scrollTo', $('#conv10'))
    // $('.messages-content').stop ().animate ({
    //   scrollTop: $('.messages-content')[0].scrollHeight
    // });

    // $('.messages-content').scrollTop($('.messages-content').prop('scrollHeight'))
    $('.mCSB_container').mCustomScrollbar("update").mCustomScrollbar('scrollTo', '100%')

  }

  // func: display time when 1 minute passed
  function setDate() {
    d = new Date()
    if (m != d.getMinutes()) {
      m = d.getMinutes();
      $('<div class="timestamp">' + d.getHours() + ':' + m + '</div>').appendTo($('.message:last'));
    }
  }

  // call Lf0
  function callChatbotApi(message) {
    // params, body, additionalParams
    return sdk.chatbotPost({}, {
      messages: [{
        type: 'unstructured',
        unstructured: {
          text: message
        }
      }]
    }, {});
  }

  function insertMessage() {
    msg = $('.message-input').val();
    if ($.trim(msg) == '') {
      return false;
    }

    // func: display this msg
    $('<div class="message message-personal">' + msg + '</div>').appendTo($('.mCSB_container')).addClass('new').attr("id","conv" + index);
    index++;
    setDate();
    $('.message-input').val(null);
    updateScrollbar();

    callChatbotApi(msg)
      .then((response) => {
        console.log(response);
        var data = response.data;
        
        // att: data.messages
        if (data.messages && data.messages.length > 0) {
          console.log('received ' + data.messages.length + ' messages');

          var messages = data.messages;

            //   {
            //     'statusCode': 200,
            //     'messages': [
            //         {
            //             "type": "unstructured",
            //             "unstructured": {
            //                 "text": msg_from_lex
            //             }
            //         }                      
            //     ]
            // }
          for (var message of messages) {
            if (message.type === 'unstructured') {
              insertResponseMessage(message.unstructured.text);
            } else if (message.type === 'structured' && message.structured.type === 'product') {
              var html = '';
              insertResponseMessage(message.structured.text);

              setTimeout(function() {
                html = '<img src="' + message.structured.payload.imageUrl + '" witdth="200" height="240" class="thumbnail" /><b>' +
                  message.structured.payload.name + '<br>$' +
                  message.structured.payload.price +
                  '</b><br><a href="#" onclick="' + message.structured.payload.clickAction + '()">' +
                  message.structured.payload.buttonLabel + '</a>';
                insertResponseMessage(html);
              }, 1100);
            } else {
              console.log('not implemented');
            }
          }
        } else {
          insertResponseMessage('Oops, something went wrong. Please try again.');
        }
      })   
      .catch((error) => {
        console.log('an error occurred', error);
        insertResponseMessage('Oops, something went wrong. Please try again.');
      });
  }

  $('.message-submit').click(function() {
    insertMessage();
  });

  $(window).on('keydown', function(e) {
    if (e.which == 13) {
      insertMessage();
      return false;
    }
  })

  function insertResponseMessage(content) {
    $('<div class="message loading new"><figure class="avatar"><img src="https://media.tenor.com/images/4c347ea7198af12fd0a66790515f958f/tenor.gif" /></figure><span></span></div>').appendTo($('.mCSB_container'));
    // updateScrollbar();

    setTimeout(function() {
      $('.message.loading').remove();
      $('<div class="message new"><figure class="avatar"><img src="https://media.tenor.com/images/4c347ea7198af12fd0a66790515f958f/tenor.gif" /></figure>' + content + '</div>').appendTo($('.mCSB_container')).addClass('new').attr("id","conv" + index);
      index++;
      setDate();
      updateScrollbar();
      i++;
    }, 500);
  }

});
