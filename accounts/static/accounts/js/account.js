class File {
  constructor(form) {
    this.form = form;

    this.csrfMiddlewareToken = $(this.form).find("input[name='csrfmiddlewaretoken']").val();
    this.maxFileSize = $(this.form).find("input[name='max_file_size']").val() || 100 * Math.pow(2, 20);
    this.fileInput = $(this.form).find("input[type='file']")[0];
    this.fileUploadButton = $(this.form).find("#file-upload-button");

    // Support 1 file only.
    this.file = this.fileInput.files[0];
    this.uploadURL = "";

    if (this.file.size > this.maxFileSize) {
      this.fileUploadButton.removeClass("disabled");
      throw new Error("File is too large.");
    }
  }

  upload() {
    this.fileUploadButton.addClass("disabled");
    this.URLUpload();
  }

  dUpload(res) {
    let headers = res.request_data.headers;
    let token = res.token;
    let _this = this;
    let formData = new FormData();

    formData.append("file", _this.file, _this.file.name);

    $.ajax({
      url: res.request_data.url,
      type: res.request_data.method,
      data: this.file,
      headers: headers,
      cache: false,
      contentType: false,
      processData: false
    })
    .done(function (data) {
      _this.finishURLUpload(token);
    })
    .fail(function (jqXHR, textStatus, errorThrown) {
      console.error(textStatus);
      _this.fileUploadButton.removeClass("disabled");
    });
  }

  finishURLUpload(token) {
    let headers = {
        "X-Transfer-Type": "SIGNED_URL",
        "X-CSRFToken": this.csrfMiddlewareToken,
        "X-Upload-Action": "FINISH",
        "X-Upload-Signature": token,
    }
    let _this = this;

    $.ajax({
      url: _this.uploadURL,
      type: "POST",
      datatype: "json",
      headers: headers,
    })
    .done(function (data) {
      alert(data.status);
    })
    .fail(function (jqXHR, textStatus, errorThrown) {
      console.error(textStatus);
      _this.fileUploadButton.removeClass("disabled");
    });
  }

  URLUpload() {
    let headers = {
        "X-Transfer-Type": "SIGNED_URL",
        "X-CSRFToken": this.csrfMiddlewareToken,
        "X-Upload-Action": "START",
        "X-Signed-URL-request": this.csrfMiddlewareToken,
    }
    let _this = this;

    $.ajax({
      url: _this.uploadURL,
      type: "POST",
      datatype: "json",
      headers: headers,
      data: {
        filename: _this.file.name,
      },
    })
    .done(function (res) {
      _this.dUpload(res);
    })
    .fail(function (jqXHR, textStatus, errorThrown) {
      console.error(textStatus);
      _this.fileUploadButton.removeClass("disabled");
    });
  }
}


$(document).ready(function() {
  $("#file-upload-form").submit(function(event) {
    event.preventDefault();

    try {
      let file = new File(event.target);
      file.upload();
    } catch(e) {
      console.error(e);
      alert(e);
      return;
    }
  });
});
