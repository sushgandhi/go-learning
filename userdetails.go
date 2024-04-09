// services/userdetails.go

func GetUserDetailsByIDHandler(c *gin.Context) {
	userID := c.Param("id")
	userStore := c.MustGet("userStore").(store.UserStore)

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Second)
	defer cancel()

	userDetail, err := userStore.GetUserDetailsByID(ctx, userID)
	if err != nil {
		// handle error
	}

	c.JSON(http.StatusOK, userDetail)
}

func AddUserHandler(c *gin.Context) {
	userDetail := c.MustGet("userDetail").(bson.M)
	userStore := c.MustGet("userStore").(store.UserStore)

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Second)
	defer cancel()

	result, err := userStore.AddUser(ctx, userDetail)
	if err != nil {
		// handle error
	}

	c.JSON(http.StatusOK, result)
}