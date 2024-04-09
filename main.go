// main.go

func main() {
	// ...

	userCollection := client.Database("yourdatabase").Collection("userdetail")

	router.GET("/userdetails/:id", middleware.WithUserStore(userCollection), services.GetUserDetailsByIDHandler)
	router.POST("/userdetails", middleware.ValidateUserDetail(), middleware.WithUserStore(userCollection), services.AddUserHandler)

	// ...
}