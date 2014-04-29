     <div class="navbar navbar-inverse navbar-fixed-top" role="navigation">
      <div class="container">
        <div class="navbar-header">
          <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-collapse">
            <span class="sr-only">Toggle navigation</span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
          </button>
          <a class="navbar-brand" href="#">FLOD</a>
        </div>
        <div class="collapse navbar-collapse">
          <ul class="nav navbar-nav navbar-right">
            <li><a href="/">Home</a></li>
            {%if logged == False or logged == None%}
            <li><a href="/login">Login</a></li>
            {%endif%}
            {%if logged == True%}
            <li><a href="/logout">Logout</a></li>
            {%endif%}
          </ul>
        </div><!--/.nav-collapse -->
      </div>
    </div>